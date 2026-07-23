from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QMessageBox

from src.llm_chat.prompt_expert_dialog import PromptExpertDialog


def _patch_dialog(dialog):
    dialog.name_edit = MagicMock()
    dialog.prompt_edit = MagicMock()
    return dialog


class TestPromptExpertDialogValidation:
    def test_save_with_valid_data(self):
        dialog = _patch_dialog(PromptExpertDialog())
        dialog.name_edit.text.return_value = "翻译专家"
        dialog.prompt_edit.toPlainText.return_value = "你是一个专业的翻译助手"

        dialog.on_save()
        assert dialog._result == {"name": "翻译专家", "system_prompt": "你是一个专业的翻译助手"}

    def test_save_empty_name(self):
        dialog = _patch_dialog(PromptExpertDialog())
        dialog.name_edit.text.return_value = ""
        dialog.prompt_edit.toPlainText.return_value = "some prompt"

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.on_save()
        assert dialog._result is None
        mock_warning.assert_called_once()

    def test_save_empty_prompt(self):
        dialog = _patch_dialog(PromptExpertDialog())
        dialog.name_edit.text.return_value = "专家名"
        dialog.prompt_edit.toPlainText.return_value = ""

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.on_save()
        assert dialog._result is None
        mock_warning.assert_called_once()

    def test_save_whitespace_name_rejected(self):
        dialog = _patch_dialog(PromptExpertDialog())
        dialog.name_edit.text.return_value = "   "
        dialog.prompt_edit.toPlainText.return_value = "some prompt"

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.on_save()
        assert dialog._result is None
        mock_warning.assert_called_once()

    def test_save_whitespace_prompt_rejected(self):
        dialog = _patch_dialog(PromptExpertDialog())
        dialog.name_edit.text.return_value = "专家名"
        dialog.prompt_edit.toPlainText.return_value = "\n\t  "

        with patch.object(QMessageBox, "warning") as mock_warning:
            dialog.on_save()
        assert dialog._result is None
        mock_warning.assert_called_once()


class TestPromptExpertDialogEditData:
    def test_edit_data_populates_name_edit(self):
        dialog = PromptExpertDialog(edit_data={"name": "code-review", "system_prompt": "review this code"})
        name_text = dialog.name_edit.text()
        assert name_text == "code-review"

    def test_edit_data_populates_prompt_edit(self):
        dialog = PromptExpertDialog(edit_data={"name": "expert", "system_prompt": "long prompt text"})
        prompt_text = dialog.prompt_edit.toPlainText()
        assert prompt_text == "long prompt text"

    def test_get_result_after_save(self):
        dialog = _patch_dialog(PromptExpertDialog())
        dialog.name_edit.text.return_value = "测试专家"
        dialog.prompt_edit.toPlainText.return_value = "测试提示词"
        dialog.on_save()
        result = dialog.get_result()
        assert result == {"name": "测试专家", "system_prompt": "测试提示词"}

    def test_get_result_before_save(self):
        dialog = _patch_dialog(PromptExpertDialog())
        dialog.name_edit.text.return_value = ""
        dialog.prompt_edit.toPlainText.return_value = ""
        with patch.object(QMessageBox, "warning"):
            dialog.on_save()
        result = dialog.get_result()
        assert result is None
