import os
import tempfile
from unittest.mock import MagicMock, patch

from src.llm_chat.input_bar import InputBar


class TestInputBarOnSend:
    def _make_input_bar(self):
        settings = MagicMock()
        settings.get.side_effect = lambda k, d="": {
            "llm_providers": [{"name": "test", "api_key": "k", "api_url": "https://x.com"}],
            "prompt_experts": [],
        }.get(k, d)
        bar = InputBar.__new__(InputBar)
        bar.settings = settings
        bar.attached_image = None
        bar.attached_image_path = None
        bar.main_window = None
        bar.model_combo = MagicMock()
        bar.model_combo.currentData.return_value = {"name": "test", "api_key": "k", "api_url": "https://x.com"}
        bar.expert_combo = MagicMock()
        bar.expert_combo.currentData.return_value = None
        bar.input_edit = MagicMock()
        bar.send_signal = MagicMock()
        return bar

    def test_send_plain_text(self):
        bar = self._make_input_bar()
        bar.input_edit.toPlainText.return_value = "hello world"
        bar.on_send()
        bar.send_signal.emit.assert_called_once_with("hello world", {"name": "test", "api_key": "k", "api_url": "https://x.com"})

    def test_send_text_with_image(self):
        bar = self._make_input_bar()
        bar.attached_image = "data:image/png;base64,abc"
        bar.input_edit.toPlainText.return_value = "看图"
        bar.on_send()
        call_args = bar.send_signal.emit.call_args[0]
        content = call_args[0]
        assert isinstance(content, list)
        assert content[0] == {"type": "text", "text": "看图"}
        assert content[1] == {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}

    def test_send_image_only(self):
        bar = self._make_input_bar()
        bar.attached_image = "data:image/jpeg;base64,xyz"
        bar.input_edit.toPlainText.return_value = ""
        bar.on_send()
        call_args = bar.send_signal.emit.call_args[0]
        content = call_args[0]
        assert isinstance(content, list)
        assert len(content) == 1
        assert content[0] == {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,xyz"}}

    def test_send_no_text_no_image(self):
        bar = self._make_input_bar()
        bar.input_edit.toPlainText.return_value = ""
        bar.on_send()
        bar.send_signal.emit.assert_not_called()

    def test_send_no_provider(self):
        bar = self._make_input_bar()
        bar.model_combo.currentData.return_value = None
        bar.input_edit.toPlainText.return_value = "hello"
        bar.on_send()
        bar.send_signal.emit.assert_not_called()

    def test_send_clears_input(self):
        bar = self._make_input_bar()
        bar.input_edit.toPlainText.return_value = "hello"
        bar.on_send()
        bar.input_edit.clear.assert_called_once()
        bar.input_edit.setFocus.assert_called_once()

    def test_send_whitespace_only_rejected(self):
        bar = self._make_input_bar()
        bar.input_edit.toPlainText.return_value = "   "
        bar.on_send()
        bar.send_signal.emit.assert_not_called()

    def test_send_with_image_and_whitespace_text(self):
        bar = self._make_input_bar()
        bar.attached_image = "data:image/png;base64,abc"
        bar.input_edit.toPlainText.return_value = "   "
        bar.on_send()
        call_args = bar.send_signal.emit.call_args[0]
        content = call_args[0]
        assert isinstance(content, list)
        assert len(content) == 1
        assert content[0]["type"] == "image_url"


class TestInputBarAttachment:
    def _make_input_bar(self):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.settings = settings
        bar.attached_image = None
        bar.attached_image_path = None
        bar.attachment_preview = MagicMock()
        bar.attachment_name = MagicMock()
        bar.attachment_bar = MagicMock()
        return bar

    def test_remove_attachment_clears_state(self):
        bar = self._make_input_bar()
        bar.attached_image = "data:image/png;base64,abc"
        bar.attached_image_path = "/path/to/img.png"
        bar.remove_attachment()
        assert bar.attached_image is None
        assert bar.attached_image_path is None
        bar.attachment_preview.clear.assert_called_once()
        bar.attachment_bar.hide.assert_called_once()


class TestInputBarImageToBase64:
    def test_image_to_base64_png(self, temp_dir):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.settings = settings

        img_path = temp_dir / "test.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\nfake png data")

        result = bar._image_to_base64(str(img_path))
        assert result is not None
        assert result.startswith("data:image/png;base64,")

    def test_image_to_base64_jpg(self, temp_dir):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.settings = settings

        img_path = temp_dir / "test.jpg"
        img_path.write_bytes(b"\xff\xd8\xff fake jpeg data")

        result = bar._image_to_base64(str(img_path))
        assert result is not None
        assert "data:image/jpeg;base64," in result

    def test_image_to_base64_nonexistent(self):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.settings = settings

        result = bar._image_to_base64("/nonexistent/path/image.png")
        assert result is None

    def test_image_to_base64_gif(self, temp_dir):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.settings = settings

        img_path = temp_dir / "test.gif"
        img_path.write_bytes(b"GIF89a fake gif data")

        result = bar._image_to_base64(str(img_path))
        assert result is not None
        assert "data:image/gif;base64," in result


class TestInputBarSelectedProvider:
    def test_get_selected_provider_valid(self):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.model_combo = MagicMock()
        bar.model_combo.currentData.return_value = {"name": "gpt-4", "api_key": "k", "api_url": "https://x.com"}
        result = bar.get_selected_provider()
        assert result is not None
        assert result["name"] == "gpt-4"

    def test_get_selected_provider_none(self):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.model_combo = MagicMock()
        bar.model_combo.currentData.return_value = None
        result = bar.get_selected_provider()
        assert result is None

    def test_get_selected_provider_custom_string(self):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.model_combo = MagicMock()
        bar.model_combo.currentData.return_value = "__custom__"
        result = bar.get_selected_provider()
        assert result is None

    def test_get_selected_expert_valid(self):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.expert_combo = MagicMock()
        bar.expert_combo.currentData.return_value = {"name": "translator", "system_prompt": "translate"}
        result = bar.get_selected_expert()
        assert result is not None
        assert result["name"] == "translator"

    def test_get_selected_expert_none(self):
        settings = MagicMock()
        bar = InputBar.__new__(InputBar)
        bar.expert_combo = MagicMock()
        bar.expert_combo.currentData.return_value = None
        result = bar.get_selected_expert()
        assert result is None
