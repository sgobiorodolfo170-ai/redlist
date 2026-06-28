from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.llm_chat.chinese_menu import _setup_chinese_context_menu
from src.theme import COLORS


class PromptExpertDialog(QDialog):
    def __init__(self, parent=None, edit_data=None):
        super().__init__(parent)
        self.setWindowTitle("新增提示词专家")
        self.setFixedSize(480, 340)
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
                color: {COLORS["text_primary"]};
                font-size: 13px;
            }}
            QLineEdit {{
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
                color: {COLORS["text_primary"]};
                background-color: #F8F9FA;
            }}
            QLineEdit:focus {{
                border-color: {COLORS["primary"]};
                background-color: white;
            }}
            QTextEdit {{
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 13px;
                color: {COLORS["text_primary"]};
                background-color: #F8F9FA;
            }}
            QTextEdit:focus {{
                border-color: {COLORS["primary"]};
                background-color: white;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("新增提示词专家")
        title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {COLORS['text_primary']};")
        layout.addWidget(title)

        name_label = QLabel("专家名称")
        name_label.setStyleSheet("font-size: 13px; font-weight: 500;")
        layout.addWidget(name_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：翻译专家、代码审查专家")
        self.name_edit.setText(self.edit_data.get("name", "") if self.edit_data else "")
        _setup_chinese_context_menu(self.name_edit)
        layout.addWidget(self.name_edit)

        prompt_label = QLabel("系统提示词")
        prompt_label.setStyleSheet("font-size: 13px; font-weight: 500;")
        layout.addWidget(prompt_label)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("请输入系统提示词，定义该专家的行为和能力...")
        self.prompt_edit.setMinimumHeight(120)
        _setup_chinese_context_menu(self.prompt_edit)
        if self.edit_data:
            self.prompt_edit.setPlainText(self.edit_data.get("system_prompt", ""))
        layout.addWidget(self.prompt_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(80, 32)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["background"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                font-size: 13px;
                color: {COLORS["text_primary"]};
            }}
            QPushButton:hover {{
                background-color: {COLORS["hover"]};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setFixedSize(80, 32)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["primary"]};
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
        name = self.name_edit.text().strip()
        prompt = self.prompt_edit.toPlainText().strip()
        if not name or not prompt:
            QMessageBox.warning(self, "提示", "请填写专家名称和系统提示词")
            return
        self._result = {"name": name, "system_prompt": prompt}
        self.accept()

    def get_result(self):
        return self._result
