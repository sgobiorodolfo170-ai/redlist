from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.theme import COLORS, NOTE_COLORS


class StickyNotePanel(QWidget):

    def __init__(self, settings, manager):
        super().__init__()
        self.settings = settings
        self.manager = manager
        self.card_editors = {}
        self.card_frames = {}

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)

        header = QLabel("便利贴")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: black;
            padding: 8px 0;
        """)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: white;
            }
            QScrollArea > QWidget > QWidget {
                background: white;
            }
        """)

        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setSpacing(4)

        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()

        add_btn = QPushButton("新建")
        add_btn.setFixedHeight(36)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
        """)
        add_btn.clicked.connect(self.add_note)
        btn_layout.addWidget(add_btn)

        self.show_btn = QPushButton("显示全部")
        self.show_btn.setFixedHeight(36)
        self.show_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #E74C3C;
                border: 1px solid #E74C3C;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #ECF0F1;
            }
        """)
        self.show_btn.clicked.connect(self.toggle_all_notes)
        btn_layout.addWidget(self.show_btn)

        layout.addLayout(btn_layout)

    def load_note_cards(self):
        self.card_editors.clear()
        self.card_frames.clear()
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for note in self.manager.notes:
            if isinstance(note, dict):
                self.create_note_card(note)

    def create_note_card(self, note):
        if not isinstance(note, dict) or 'id' not in note:
            return

        card = QFrame()
        card.setFixedHeight(50)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        color_key = note.get('color', 'yellow')
        bg_color = NOTE_COLORS.get(color_key, NOTE_COLORS['yellow'])

        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 4px;
                margin: 2px 0;
                border: none;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)

        text = note.get('text', '')
        is_placeholder = not text
        display_text = text or '# 单击显示/隐藏，双击删除'
        text_label = QLabel(display_text)
        text_label.setWordWrap(True)
        text_color = '#7F8C8D' if is_placeholder else 'black'
        text_label.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                color: {text_color};
                font-size: 15px;
                padding: 2px;
            }}
        """)
        note_id = note.get('id')
        if not note_id or not isinstance(note_id, str):
            return
        layout.addWidget(text_label)

        card.mousePressEvent = lambda event, nid=note_id: self.on_card_click(event, nid)
        card.mouseDoubleClickEvent = lambda event, nid=note_id: self.on_card_double_click(event, nid)

        self.card_editors[note_id] = text_label
        self.card_frames[note_id] = card

        self.cards_layout.addWidget(card)

    def refresh_card_color(self, note_id, color_key):
        if not note_id or not isinstance(note_id, str):
            return
        if hasattr(self, 'card_frames') and note_id in self.card_frames:
            card = self.card_frames[note_id]
            bg_color = NOTE_COLORS.get(color_key, NOTE_COLORS['yellow'])
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border-radius: 4px;
                    margin: 2px 0;
                    border: none;
                }}
            """)

    def refresh_card_text(self, note_id, text):
        if not note_id or not isinstance(note_id, str):
            return
        if hasattr(self, 'card_editors') and note_id in self.card_editors:
            label = self.card_editors[note_id]
            is_placeholder = not text
            display_text = text or '# 单击显示/隐藏，双击删除'
            label.setText(display_text)
            text_color = '#7F8C8D' if is_placeholder else 'black'
            label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: {text_color};
                    font-size: 15px;
                    padding: 2px;
                }}
            """)

    def on_card_click(self, event, note_id):
        if event.button() == Qt.MouseButton.LeftButton:
            self.manager.toggle_note(note_id)

    def on_card_double_click(self, event, note_id):
        msg = QMessageBox(self)
        msg.setWindowTitle('确认删除')
        msg.setText('确定要删除这个便利贴吗？')
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QLabel {
                color: #2C3E50;
                font-size: 14px;
            }
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        reply = msg.exec()
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_note(note_id)

    def add_note(self):
        self.manager.create_note()
        QTimer.singleShot(300, self.load_note_cards)

    def toggle_all_notes(self):
        manager_notes = getattr(self.manager, 'notes', [])
        valid_notes = [n for n in manager_notes if isinstance(n, dict) and isinstance(n.get('id'), str)]
        note_ids = [note['id'] for note in valid_notes]

        any_visible = False
        for nid in note_ids:
            if nid in self.manager.note_windows:
                if self.manager.note_windows[nid].isVisible():
                    any_visible = True
                    break

        if any_visible:
            for window in self.manager.note_windows.values():
                window.hide()
            self.show_btn.setText("显示全部")
        else:
            if note_ids:
                for nid in note_ids:
                    if nid in self.manager.note_windows:
                        self.manager.note_windows[nid].show()
                        self.manager.note_windows[nid].activateWindow()
                    else:
                        note_data = None
                        for note in valid_notes:
                            if note.get('id') == nid:
                                note_data = note.copy()
                                break
                        if note_data:
                            self.manager.create_note(note_data)
            else:
                self.manager.create_note()
                QTimer.singleShot(300, self.load_note_cards)
            self.show_btn.setText("隐藏全部")

    def delete_note(self, note_id):
        self.manager.delete_note(note_id)
        QTimer.singleShot(100, self.load_note_cards)

    def refresh_cards(self):
        self.load_note_cards()
