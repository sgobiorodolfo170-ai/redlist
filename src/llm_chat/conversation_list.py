from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QPushButton, QInputDialog, QMessageBox, QVBoxLayout, QWidget,
)

from src.theme import COLORS
from src.utils.logger import get_logger

logger = get_logger("ConversationList")


class ConversationList(QWidget):
    conversation_selected = pyqtSignal(str)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.current_id = None
        self.init_ui()

    def init_ui(self):
        self.setMinimumWidth(0)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: #F8F9FA;
            }}
            QListWidget {{
                border: none;
                background-color: transparent;
                outline: none;
            }}
            QListWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid #E9ECEF;
                color: {COLORS['text_primary']};
                font-size: 13px;
            }}
            QListWidget::item:hover {{
                background-color: {COLORS['hover']};
            }}
            QListWidget::item:selected {{
                background-color: {COLORS['primary']};
                color: white;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 6, 8, 6)

        header_label = QLabel("会话列表")
        header_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {COLORS['text_primary']}; background: transparent;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        new_btn = QPushButton("+")
        new_btn.setFixedSize(24, 24)
        new_btn.setToolTip("新建会话")
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
        """)
        new_btn.clicked.connect(self.on_new_conversation)
        header_layout.addWidget(new_btn)

        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.on_context_menu)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)

    def load_conversations(self):
        self.list_widget.clear()
        convs = self.manager.list_conversations()
        for conv in convs:
            item = QListWidgetItem()
            conv_id = conv['id']
            title = conv['title']
            item.setText(title)
            item.setData(Qt.ItemDataRole.UserRole, conv_id)
            if conv_id == self.current_id:
                item.setSelected(True)
            self.list_widget.addItem(item)

    def on_new_conversation(self):
        providers = self._get_settings_providers()
        if not providers:
            QMessageBox.information(self, "提示", "请先在模型选择中添加自定义模型提供商")
            return
        model_config = providers[0]
        conv_id = self.manager.create_conversation(model_config)
        self.current_id = conv_id
        self.load_conversations()
        self.conversation_selected.emit(conv_id)

    def on_item_clicked(self, item):
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        if conv_id != self.current_id:
            self.current_id = conv_id
            self.conversation_selected.emit(conv_id)

    def on_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 24px;
                font-size: 13px;
                color: {COLORS['text_primary']};
            }}
            QMenu::item:hover {{
                background-color: {COLORS['hover']};
                border-radius: 4px;
            }}
        """)

        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")

        action = menu.exec(self.list_widget.mapToGlobal(pos))
        if action == rename_action:
            self.on_rename(conv_id)
        elif action == delete_action:
            self.on_delete(conv_id)

    def on_rename(self, conv_id):
        data = self.manager.get_conversation(conv_id)
        if data is None:
            return
        old_title = data.get('title', '')
        new_title, ok = QInputDialog.getText(self, "重命名会话", "请输入新名称:", text=old_title)
        if ok and new_title.strip():
            self.manager.rename_conversation(conv_id, new_title.strip())
            self.load_conversations()

    def on_delete(self, conv_id):
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除该会话吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.delete_conversation(conv_id)
            if self.current_id == conv_id:
                self.current_id = None
            self.load_conversations()

    def _get_settings_providers(self):
        return self.manager.settings.get('llm_providers', [])
