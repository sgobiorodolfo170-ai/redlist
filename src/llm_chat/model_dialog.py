from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QLabel,
)

from src.llm_chat.chinese_menu import _setup_chinese_context_menu
from src.theme import COLORS


class ModelDialog(QDialog):
    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.setWindowTitle("自定义模型提供商")
        self.setFixedSize(420, 260)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._result = None
        self.edit_data = edit_data
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: white;
                border-radius: 8px;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QLineEdit {{
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
                color: {COLORS['text_primary']};
                background-color: #F8F9FA;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
                background-color: white;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("自定义模型提供商")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text_primary']};")
        layout.addWidget(title)

        desc = QLabel("填写兼容 OpenAI 接口的 API 地址和密钥")
        desc.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://api.openai.com/v1")
        self.url_edit.setText(self.edit_data.get('api_url', '') if self.edit_data else '')
        form.addRow("接口地址:", self.url_edit)
        _setup_chinese_context_menu(self.url_edit)

        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("sk-...")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setText(self.edit_data.get('api_key', '') if self.edit_data else '')
        form.addRow("API Key:", self.key_edit)
        _setup_chinese_context_menu(self.key_edit)

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("gpt-4o")
        self.model_edit.setText(self.edit_data.get('model_name', '') if self.edit_data else '')
        form.addRow("模型名称:", self.model_edit)
        _setup_chinese_context_menu(self.model_edit)

        layout.addLayout(form)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(80, 32)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setFixedSize(80, 32)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
        """)
        save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def on_save(self):
        url = self.url_edit.text().strip()
        key = self.key_edit.text().strip()
        model = self.model_edit.text().strip()
        if not url or not key or not model:
            QMessageBox.warning(self, "提示", "请填写完整的接口地址、API Key 和模型名称")
            return
        if not url.startswith('https://') and not url.startswith('http://'):
            QMessageBox.warning(self, "提示", "接口地址请以 http:// 或 https:// 开头")
            return
        name = model
        self._result = {"name": name, "api_url": url.rstrip('/'), "api_key": key, "model_name": model}
        self.accept()

    def get_result(self):
        return self._result
