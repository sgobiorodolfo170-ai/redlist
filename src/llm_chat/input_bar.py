import base64
import os

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.llm_chat.chinese_menu import _setup_chinese_context_menu
from src.llm_chat.model_dialog import ModelDialog
from src.llm_chat.prompt_expert_dialog import PromptExpertDialog
from src.theme import COLORS


class InputBar(QWidget):
    send_signal = pyqtSignal(str, object)
    screenshot_requested = pyqtSignal()

    def __init__(self, settings, main_window=None):
        super().__init__()
        self.settings = settings
        self.main_window = main_window
        self.attached_image = None
        self.attached_image_path = None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: white;
            }}
            QTextEdit {{
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: {COLORS["text_primary"]};
                background-color: #F8F9FA;
            }}
            QTextEdit:focus {{
                border-color: {COLORS["primary"]};
                background-color: white;
            }}
            QTextEdit::placeholder {{
                color: #ADB5BD;
            }}
            QComboBox {{
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 6px 8px;
                font-size: 12px;
                color: {COLORS["text_primary"]};
                background-color: #F8F9FA;
                min-width: 40px;
            }}
            QComboBox:focus {{
                border-color: {COLORS["primary"]};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #DEE2E6;
                background-color: white;
                selection-background-color: {COLORS["hover"]};
                selection-color: {COLORS["text_primary"]};
                padding: 4px;
            }}
            QPushButton {{
                font-size: 13px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 8)
        layout.setSpacing(4)

        self.attachment_bar = QFrame()
        self.attachment_bar.setFixedHeight(40)
        self.attachment_bar.setStyleSheet("background: transparent;")
        self.attachment_bar.hide()
        attachment_layout = QHBoxLayout(self.attachment_bar)
        attachment_layout.setContentsMargins(4, 0, 4, 0)
        attachment_layout.setSpacing(6)

        self.attachment_preview = QLabel()
        self.attachment_preview.setFixedSize(32, 32)
        self.attachment_preview.setStyleSheet("""
            QLabel {
                border: 1px solid #DEE2E6;
                border-radius: 4px;
                background-color: #F8F9FA;
            }
        """)
        attachment_layout.addWidget(self.attachment_preview)

        self.attachment_name = QLabel()
        self.attachment_name.setStyleSheet(
            f"font-size: 11px; color: {COLORS['text_secondary']}; background: transparent;"
        )
        attachment_layout.addWidget(self.attachment_name)
        attachment_layout.addStretch()

        remove_attachment_btn = QPushButton("✕")
        remove_attachment_btn.setFixedSize(20, 20)
        remove_attachment_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
                color: #ADB5BD;
            }
            QPushButton:hover {
                color: #E74C3C;
            }
        """)
        remove_attachment_btn.clicked.connect(self.remove_attachment)
        attachment_layout.addWidget(remove_attachment_btn)

        layout.addWidget(self.attachment_bar)

        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("输入消息... (Enter 发送，Shift+Enter 换行)")
        self.input_edit.setMinimumHeight(60)
        self.input_edit.installEventFilter(self)
        _setup_chinese_context_menu(self.input_edit)
        layout.addWidget(self.input_edit, 1)

        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(6)

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(32, 32)
        self.add_btn.setToolTip("添加附件")
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["background"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                color: {COLORS["text_primary"]};
            }}
            QPushButton:hover {{
                background-color: {COLORS["hover"]};
            }}
        """)
        self.add_btn.clicked.connect(self.on_add_clicked)
        toolbar_row.addWidget(self.add_btn)

        self.model_combo = QComboBox()
        self.model_combo.setToolTip("选择模型")
        self.model_combo.setMinimumWidth(50)
        self.model_combo.activated.connect(self.on_model_changed)
        self.model_combo.view().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.model_combo.view().customContextMenuRequested.connect(self._show_model_context_menu)
        toolbar_row.addWidget(self.model_combo)

        self.expert_combo = QComboBox()
        self.expert_combo.setToolTip("选择提示词专家")
        self.expert_combo.setMinimumWidth(67)
        self.expert_combo.activated.connect(self.on_expert_changed)
        self.expert_combo.view().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.expert_combo.view().customContextMenuRequested.connect(self._show_expert_context_menu)
        toolbar_row.addWidget(self.expert_combo)

        toolbar_row.addStretch()

        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(52, 32)
        self.send_btn.setStyleSheet(f"""
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
            QPushButton:disabled {{
                background-color: #BDC3C7;
            }}
        """)
        self.send_btn.clicked.connect(self.on_send)
        toolbar_row.addWidget(self.send_btn)

        layout.addLayout(toolbar_row)

        self.reload_providers()
        self.reload_experts()

    def on_add_clicked(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                font-size: 13px;
                color: {COLORS["text_primary"]};
            }}
            QMenu::item:hover {{
                background-color: {COLORS["hover"]};
                border-radius: 4px;
            }}
        """)

        screenshot_action = menu.addAction("📷  截图")
        file_action = menu.addAction("📄  添加文件")
        action = menu.exec(self.add_btn.mapToGlobal(self.add_btn.rect().bottomLeft()))

        if action == screenshot_action:
            self.screenshot_requested.emit()
        elif action == file_action:
            self.on_add_file()

    def on_add_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*)"
        )
        if file_path:
            self.set_attachment(file_path)

    def set_attachment(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                self.attachment_preview.setPixmap(
                    pixmap.scaled(
                        32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                    )
                )
            self.attached_image_path = file_path
            self.attached_image = self._image_to_base64(file_path)
            self.attachment_name.setText(os.path.basename(file_path))
            self.attachment_bar.show()

    def remove_attachment(self):
        self.attached_image = None
        self.attached_image_path = None
        self.attachment_preview.clear()
        self.attachment_bar.hide()

    def _image_to_base64(self, file_path):
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            ext = os.path.splitext(file_path)[1].lower().replace(".", "")
            if ext == "jpg":
                ext = "jpeg"
            return f"data:image/{ext};base64,{base64.b64encode(data).decode()}"
        except Exception:
            return None

    def reload_providers(self):
        current = self.model_combo.currentData()
        self.model_combo.blockSignals(True)
        try:
            self.model_combo.clear()
            providers = self.settings.get("llm_providers", [])
            for p in providers:
                self.model_combo.addItem(p.get("name", p.get("model_name", "")), p)
            if providers:
                self.model_combo.insertSeparator(self.model_combo.count())
            self.model_combo.addItem("✚ 自定义...", "__custom__")

            if isinstance(current, dict):
                for i in range(self.model_combo.count()):
                    data = self.model_combo.itemData(i)
                    if isinstance(data, dict) and data.get("name") == current.get("name"):
                        self.model_combo.setCurrentIndex(i)
                        break
        finally:
            self.model_combo.blockSignals(False)

    def reload_experts(self):
        current = self.expert_combo.currentText()
        self.expert_combo.blockSignals(True)
        self.expert_combo.clear()
        self.expert_combo.addItem("无", None)
        experts = self.settings.get("prompt_experts", [])
        for e in experts:
            self.expert_combo.addItem(e.get("name", ""), e)
        if experts:
            self.expert_combo.insertSeparator(self.expert_combo.count())
        self.expert_combo.addItem("✚ 增加专家...", "__add_expert__")

        if current:
            idx = self.expert_combo.findText(current)
            if idx >= 0:
                self.expert_combo.setCurrentIndex(idx)
        self.expert_combo.blockSignals(False)

    def on_model_changed(self, index):
        data = self.model_combo.itemData(index)
        if data == "__custom__":
            dialog = ModelDialog(self)
            if dialog.exec():
                result = dialog.get_result()
                if result:
                    providers = list(self.settings.get("llm_providers", []))
                    providers.append(result)
                    self.settings.set("llm_providers", providers, immediate=True)
                    self.reload_providers()
                    for i in range(self.model_combo.count()):
                        d = self.model_combo.itemData(i)
                        if isinstance(d, dict) and d.get("name") == result["name"]:
                            self.model_combo.setCurrentIndex(i)
                            break

    def on_expert_changed(self, index):
        data = self.expert_combo.itemData(index)
        if data == "__add_expert__":
            dialog = PromptExpertDialog(self)
            if dialog.exec():
                result = dialog.get_result()
                if result:
                    experts = list(self.settings.get("prompt_experts", []))
                    experts.append(result)
                    self.settings.set("prompt_experts", experts, immediate=True)
                    self.reload_experts()
                    for i in range(self.expert_combo.count()):
                        d = self.expert_combo.itemData(i)
                        if isinstance(d, dict) and d.get("name") == result["name"]:
                            self.expert_combo.setCurrentIndex(i)
                            break

    def get_selected_provider(self):
        data = self.model_combo.currentData()
        if isinstance(data, dict):
            return data
        return None

    def get_selected_expert(self):
        data = self.expert_combo.currentData()
        if isinstance(data, dict):
            return data
        return None

    def eventFilter(self, obj, event):
        if obj is self.input_edit and event.type() == QEvent.Type.KeyPress:
            if (
                event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and event.modifiers() == Qt.KeyboardModifier.NoModifier
            ):
                self.on_send()
                return True
        return super().eventFilter(obj, event)

    def on_send(self):
        text = self.input_edit.toPlainText().strip()
        model_config = self.get_selected_provider()
        if not model_config:
            return
        content = text
        if self.attached_image and text:
            content = [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": self.attached_image}},
            ]
        elif self.attached_image and not text:
            content = [
                {"type": "image_url", "image_url": {"url": self.attached_image}},
            ]
        elif not text:
            return

        self.input_edit.clear()
        self.input_edit.setFocus()
        self.send_signal.emit(content, model_config)

    def _show_model_context_menu(self, pos):
        index = self.model_combo.view().indexAt(pos)
        if not index.isValid():
            return
        data = self.model_combo.itemData(index.row())
        if not isinstance(data, dict):
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                font-size: 13px;
                color: {COLORS["text_primary"]};
            }}
            QMenu::item:hover {{
                background-color: {COLORS["hover"]};
                border-radius: 4px;
            }}
        """)

        edit_action = menu.addAction("编辑")
        menu.addSeparator()
        delete_action = menu.addAction("删除")

        action = menu.exec(self.model_combo.view().viewport().mapToGlobal(pos))
        if action == edit_action:
            dialog = ModelDialog(self, edit_data=data)
            if dialog.exec():
                result = dialog.get_result()
                if result:
                    providers = list(self.settings.get("llm_providers", []))
                    for i, p in enumerate(providers):
                        if p.get("name") == data.get("name"):
                            providers[i] = result
                            break
                    self.settings.set("llm_providers", providers, immediate=True)
                    self.reload_providers()
                    for i in range(self.model_combo.count()):
                        d = self.model_combo.itemData(i)
                        if isinstance(d, dict) and d.get("name") == result["name"]:
                            self.model_combo.setCurrentIndex(i)
                            break
        elif action == delete_action:
            providers = list(self.settings.get("llm_providers", []))
            providers = [p for p in providers if p.get("name") != data.get("name")]
            self.settings.set("llm_providers", providers, immediate=True)
            self.reload_providers()

    def _show_expert_context_menu(self, pos):
        index = self.expert_combo.view().indexAt(pos)
        if not index.isValid():
            return
        data = self.expert_combo.itemData(index.row())
        if not isinstance(data, dict):
            return

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                font-size: 13px;
                color: {COLORS["text_primary"]};
            }}
            QMenu::item:hover {{
                background-color: {COLORS["hover"]};
                border-radius: 4px;
            }}
        """)

        edit_action = menu.addAction("编辑")
        menu.addSeparator()
        delete_action = menu.addAction("删除")

        action = menu.exec(self.expert_combo.view().viewport().mapToGlobal(pos))
        if action == edit_action:
            dialog = PromptExpertDialog(self, edit_data=data)
            if dialog.exec():
                result = dialog.get_result()
                if result:
                    experts = list(self.settings.get("prompt_experts", []))
                    for i, e in enumerate(experts):
                        if e.get("name") == data.get("name"):
                            experts[i] = result
                            break
                    self.settings.set("prompt_experts", experts, immediate=True)
                    self.reload_experts()
                    for i in range(self.expert_combo.count()):
                        d = self.expert_combo.itemData(i)
                        if isinstance(d, dict) and d.get("name") == result["name"]:
                            self.expert_combo.setCurrentIndex(i)
                            break
        elif action == delete_action:
            experts = list(self.settings.get("prompt_experts", []))
            experts = [e for e in experts if e.get("name") != data.get("name")]
            self.settings.set("prompt_experts", experts, immediate=True)
            self.reload_experts()

    def set_main_window(self, main_window):
        self.main_window = main_window
