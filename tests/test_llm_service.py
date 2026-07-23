import json
import unittest
from unittest.mock import Mock, patch

from src.llm_chat.llm_service import LLMService


def _make_sse_bytes(content: str, encoding: str = "utf-8") -> bytes:
    """Build a single SSE data line"""
    payload = json.dumps({
        "choices": [{"delta": {"content": content}, "index": 0, "finish_reason": None}],
        "model": "test",
        "object": "chat.completion.chunk",
    }, ensure_ascii=False)
    return f"data: {payload}\n\n".encode(encoding)


def _make_sse_done() -> bytes:
    return b"data: [DONE]\n\n"


def _make_sse_empty_choices() -> bytes:
    payload = json.dumps({"choices": []})
    return f"data: {payload}\n\n".encode("utf-8")


def _make_sse_bad_json() -> bytes:
    return b"data: {not json}\n\n"


def _make_mock_response(lines, status=200, encoding="utf-8"):
    """Create a mock requests.Response that yields SSE lines"""
    mock_resp = Mock(spec=__import__("requests").Response, status_code=status, encoding=encoding)
    mock_resp.iter_lines.return_value = lines
    mock_resp.headers = {}
    mock_resp.__enter__ = Mock(return_value=mock_resp)
    mock_resp.__exit__ = Mock(return_value=None)
    return mock_resp


class TestLLMServiceSSE(unittest.TestCase):
    """Mock SSE stream tests — no QApp or network needed"""

    def setUp(self):
        self.model_config = {
            "name": "test",
            "api_url": "https://api.test.com/v1",
            "api_key": "sk-test12345678",
            "model_name": "test-model",
        }
        self.messages = [{"role": "user", "content": "hello"}]

    @patch("src.llm_chat.llm_service.requests.post")
    def test_normal_utf8_stream(self, mock_post):
        """Scenario 1: normal UTF-8 streaming"""
        lines = [_make_sse_bytes("你好"), _make_sse_done()]
        mock_post.return_value = _make_mock_response(lines)

        service = self._make_service()
        service.run()

        service.chunk_received.emit.assert_called_once_with("你好")
        service.finished.emit.assert_called_once()
        service.error.emit.assert_not_called()

    @patch("src.llm_chat.llm_service.requests.post")
    def test_gbk_encoded_stream(self, mock_post):
        """Scenario 2: GBK-encoded SSE line — graceful degradation with U+FFFD"""
        gbk_bytes = _make_sse_bytes("你好", encoding="gbk")
        lines = [gbk_bytes, _make_sse_done()]
        mock_post.return_value = _make_mock_response(lines)

        service = self._make_service()
        service.run()

        # GBK content in SSE stream produces U+FFFD replacement chars
        service.chunk_received.emit.assert_called_once()
        service.error.emit.assert_not_called()

    @patch("src.llm_chat.llm_service.requests.post")
    def test_binary_corrupted_stream(self, mock_post):
        """Scenario 3: binary corrupted line — safe_decode replaces with U+FFFD"""
        lines = [b"data: {\"choices\":[{\"delta\":{\"content\":\"\xff\xfe\"}}]}\n\n", _make_sse_done()]
        mock_post.return_value = _make_mock_response(lines)

        service = self._make_service()
        service.run()

        service.chunk_received.emit.assert_called_once()
        service.error.emit.assert_not_called()

    @patch("src.llm_chat.llm_service.requests.post")
    def test_401_auth_error(self, mock_post):
        """Scenario 4: 401 unauthorized"""
        mock_post.return_value = _make_mock_response([], status=401)
        mock_post.return_value.ok = False
        mock_post.return_value.raise_for_status.side_effect = __import__("requests").exceptions.HTTPError(
            response=mock_post.return_value
        )

        service = self._make_service()
        service.run()

        service.error.emit.assert_called_once()
        signal = service.error.emit.call_args[0][0]
        self.assertTrue(signal.startswith("[AUTH_ERROR]"), signal)

    @patch("src.llm_chat.llm_service.requests.post")
    def test_404_model_not_found(self, mock_post):
        """Scenario 5: 404 model not found"""
        mock_post.return_value = _make_mock_response([], status=404)
        mock_post.return_value.ok = False
        mock_post.return_value.raise_for_status.side_effect = __import__("requests").exceptions.HTTPError(
            response=mock_post.return_value
        )

        service = self._make_service()
        service.run()

        service.error.emit.assert_called_once()
        signal = service.error.emit.call_args[0][0]
        self.assertTrue(signal.startswith("[MODEL_NOT_FOUND]"), signal)

    @patch("src.llm_chat.llm_service.requests.post")
    def test_connection_error(self, mock_post):
        """Scenario 6: connection refused"""
        mock_post.side_effect = __import__("requests").exceptions.ConnectionError()

        service = self._make_service()
        service.run()

        service.error.emit.assert_called_once()
        signal = service.error.emit.call_args[0][0]
        self.assertTrue(signal.startswith("[CONNECTION_ERROR]"), signal)

    @patch("src.llm_chat.llm_service.requests.post")
    def test_timeout(self, mock_post):
        """Scenario 7: request timeout"""
        mock_post.side_effect = __import__("requests").exceptions.Timeout()

        service = self._make_service()
        service.run()

        service.error.emit.assert_called_once()
        signal = service.error.emit.call_args[0][0]
        self.assertTrue(signal.startswith("[TIMEOUT]"), signal)

    def test_invalid_config(self):
        """Scenario 8: missing config fields"""
        service = self._make_service()
        service.model_config = {"name": "bad"}
        service.run()

        service.error.emit.assert_called_once()
        signal = service.error.emit.call_args[0][0]
        self.assertTrue(signal.startswith("[INVALID_CONFIG]"), signal)

    @patch("src.llm_chat.llm_service.requests.post")
    def test_done_stops_early(self, mock_post):
        """Scenario 9: [DONE] stops processing even with more data"""
        lines = [_make_sse_bytes("foo"), _make_sse_done(), _make_sse_bytes("bar")]
        mock_post.return_value = _make_mock_response(lines)

        service = self._make_service()
        service.run()

        calls = service.chunk_received.emit.call_args_list
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][0], "foo")
        service.error.emit.assert_not_called()

    @patch("src.llm_chat.llm_service.requests.post")
    def test_empty_choices_skipped(self, mock_post):
        """Scenario 10: empty choices line — skip, no crash"""
        lines = [_make_sse_empty_choices(), _make_sse_bytes("ok"), _make_sse_done()]
        mock_post.return_value = _make_mock_response(lines)

        service = self._make_service()
        service.run()

        service.chunk_received.emit.assert_called_once_with("ok")
        service.error.emit.assert_not_called()

    @patch("src.llm_chat.llm_service.requests.post")
    def test_bad_json_skipped(self, mock_post):
        """Scenario 11: malformed JSON line — skip, continue"""
        lines = [_make_sse_bad_json(), _make_sse_bytes("ok"), _make_sse_done()]
        mock_post.return_value = _make_mock_response(lines)

        service = self._make_service()
        service.run()

        service.chunk_received.emit.assert_called_once_with("ok")
        service.error.emit.assert_not_called()

    @patch("src.llm_chat.llm_service.requests.post")
    def test_cancel_stops_stream(self, mock_post):
        """Scenario 12: cancel() stops processing immediately"""
        lines = [_make_sse_bytes("a"), _make_sse_bytes("b"), _make_sse_done()]
        mock_post.return_value = _make_mock_response(lines)

        service = self._make_service()
        service._cancelled = True
        service.run()

        service.chunk_received.emit.assert_not_called()
        service.finished.emit.assert_not_called()
        service.error.emit.assert_not_called()

    @patch("src.llm_chat.llm_service.requests.post")
    def test_stream_timeout_emits_error(self, mock_post):
        """Scenario 13: stream-level timeout triggers [TIMEOUT]"""
        # Yield one line then sleep — timeout triggers before [DONE]
        def slow_lines():
            yield _make_sse_bytes("a")
            while True:
                yield None

        mock_post.return_value = _make_mock_response(slow_lines())

        service = self._make_service()
        service.STREAM_TIMEOUT = 0.001
        service.run()

        service.error.emit.assert_called_once()
        signal = service.error.emit.call_args[0][0]
        self.assertTrue(signal.startswith("[TIMEOUT]"), signal)

    # --- helpers ---

    def _make_service(self):
        service = LLMService(self.messages, self.model_config)
        service.chunk_received = Mock()
        service.finished = Mock()
        service.error = Mock()
        return service


if __name__ == "__main__":
    unittest.main()
