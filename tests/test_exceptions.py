import unittest

from src.llm_chat.exceptions import (
    AuthError,
    ConnectionError_,
    InvalidConfigError,
    LLMError,
    ModelNotFoundError,
    RateLimitError,
    StreamDecodeError,
    TimeoutError,
    format_error_signal,
    parse_error_signal,
)


class TestExceptionHierarchy(unittest.TestCase):
    def test_llm_error_base(self):
        e = LLMError("test")
        self.assertEqual(e.code, "LLM_ERROR")
        self.assertEqual(str(e), "test")

    def test_auth_error(self):
        e = AuthError()
        self.assertEqual(e.code, "AUTH_ERROR")
        self.assertIn("API Key", str(e))

    def test_auth_error_custom_message(self):
        e = AuthError("自定义消息")
        self.assertEqual(e.code, "AUTH_ERROR")
        self.assertEqual(str(e), "自定义消息")

    def test_rate_limit_error(self):
        e = RateLimitError()
        self.assertEqual(e.code, "RATE_LIMIT_ERROR")

    def test_stream_decode_error(self):
        e = StreamDecodeError()
        self.assertEqual(e.code, "STREAM_DECODE_ERROR")

    def test_timeout_error(self):
        e = TimeoutError()
        self.assertEqual(e.code, "TIMEOUT")

    def test_model_not_found_error(self):
        e = ModelNotFoundError("gpt-5")
        self.assertEqual(e.code, "MODEL_NOT_FOUND")
        self.assertIn("gpt-5", str(e))

    def test_model_not_found_empty(self):
        e = ModelNotFoundError()
        self.assertIn("不存在", str(e))

    def test_invalid_config_error(self):
        e = InvalidConfigError()
        self.assertEqual(e.code, "INVALID_CONFIG")

    def test_connection_error(self):
        e = ConnectionError_()
        self.assertEqual(e.code, "CONNECTION_ERROR")


class TestFormatParseRoundTrip(unittest.TestCase):
    def test_round_trip_auth_error(self):
        e = AuthError("密钥无效")
        signal = format_error_signal(e)
        code, msg = parse_error_signal(signal)
        self.assertEqual(code, "AUTH_ERROR")
        self.assertEqual(msg, "密钥无效")

    def test_round_trip_timeout(self):
        e = TimeoutError("请求超时")
        signal = format_error_signal(e)
        self.assertTrue(signal.startswith("[TIMEOUT]"))
        self.assertTrue(signal.endswith("请求超时"))

    def test_round_trip_custom_llm_error(self):
        e = LLMError("HTTP 500", code="HTTP_ERROR")
        signal = format_error_signal(e)
        code, msg = parse_error_signal(signal)
        self.assertEqual(code, "HTTP_ERROR")
        self.assertEqual(msg, "HTTP 500")

    def test_parse_plain_string(self):
        code, msg = parse_error_signal("普通错误")
        self.assertEqual(code, "LLM_ERROR")
        self.assertEqual(msg, "普通错误")

    def test_parse_empty_string(self):
        code, msg = parse_error_signal("")
        self.assertEqual(code, "LLM_ERROR")
        self.assertEqual(msg, "")

    def test_format_invalid_config(self):
        e = InvalidConfigError("URL 格式错误")
        signal = format_error_signal(e)
        self.assertEqual(signal, "[INVALID_CONFIG] URL 格式错误")

    def test_isinstance_check(self):
        for exc_cls in [AuthError, TimeoutError, RateLimitError, StreamDecodeError,
                        ModelNotFoundError, InvalidConfigError, ConnectionError_]:
            self.assertTrue(issubclass(exc_cls, LLMError))


if __name__ == "__main__":
    unittest.main()
