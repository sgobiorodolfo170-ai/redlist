from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtWidgets import QMenu, QTextEdit, QVBoxLayout, QWidget

from src.theme import NOTE_COLORS
from src.utils.geometry import is_horizontal_overlap, is_vertical_overlap


class StickyNoteWindow(QWidget):
    NOTE_WIDTH = 320
    NOTE_HEIGHT = 250

    def __init__(self, note_id, text, color, x, y, manager):
        super().__init__()
        self.note_id = note_id
        self.color = color
        self.manager = manager
        self.dragging = False
        self.drag_position = QPoint()
        self.is_magnet = False
        self.magnet_targets = []
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._do_save_content)
        self._pending_text = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMouseTracking(True)
        self.setFixedSize(self.NOTE_WIDTH, self.NOTE_HEIGHT)
        self.move(x, y)

        self.installEventFilter(self)

        self.init_ui(text)

    def init_ui(self, text):
        bg_color = NOTE_COLORS.get(self.color, NOTE_COLORS["yellow"])

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                color: black;
                font-size: 15px;
                padding: 4px;
            }
        """)
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.text_edit.textChanged.connect(self.on_text_changed)
        self.text_edit.installEventFilter(self)
        layout.addWidget(self.text_edit)

    def on_text_changed(self):
        self._pending_text = self.text_edit.toPlainText()
        self._save_timer.start(1000)

    def _do_save_content(self):
        if self._pending_text is not None:
            self.manager.update_note_content(self.note_id, self._pending_text)
            self._pending_text = None

    def closeEvent(self, event):
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._do_save_content()
        super().closeEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                color: black;
                background-color: white;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
                color: black;
            }
        """)

        copy_action = menu.addAction("复制")
        copy_action.triggered.connect(lambda: self.text_edit.copy())

        paste_action = menu.addAction("粘贴")
        paste_action.triggered.connect(lambda: self.text_edit.paste())

        menu.exec(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        colors = list(NOTE_COLORS.keys())
        current_index = colors.index(self.color) if self.color in colors else 0
        next_index = (current_index + 1) % len(colors)
        self.color = colors[next_index]
        bg_color = NOTE_COLORS[self.color]
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 4px;
            }}
        """)
        self.manager.update_note_color(self.note_id, self.color)

    def set_color(self, color_key):
        self.color = color_key
        bg_color = NOTE_COLORS[color_key]

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 4px;
            }}
        """)
        self.manager.update_note_color(self.note_id, self.color)

    def set_content(self, text):
        self.text_edit.setPlainText(text)
        self.manager.update_note_content(self.note_id, text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.magnet_targets = []

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            new_geo = QRect(new_pos, self.size())
            adjusted_pos = self.avoid_overlap(new_geo)
            self.move(adjusted_pos)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self.try_magnet()

    def eventFilter(self, obj, event):
        if hasattr(self, "text_edit") and obj == self.text_edit:
            if event.type() == event.Type.MouseButtonDblClick:
                self.mouseDoubleClickEvent(event)
                return True
            if event.type() == event.Type.ContextMenu:
                self.contextMenuEvent(event)
                return True

        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.magnet_targets = []
                return True
        elif event.type() == event.Type.MouseMove:
            if self.dragging:
                new_pos = event.globalPosition().toPoint() - self.drag_position
                new_geo = QRect(new_pos, self.size())
                adjusted_pos = self.avoid_overlap(new_geo)
                self.move(adjusted_pos)
                return True
        elif event.type() == event.Type.MouseButtonRelease:
            if self.dragging:
                self.dragging = False
                self.try_magnet()
                return True
        return super().eventFilter(obj, event)

    def avoid_overlap(self, new_geo):
        max_iterations = 10
        for _ in range(max_iterations):
            moved = False
            for other_id, other_window in self.manager.note_windows.items():
                if other_id == self.note_id:
                    continue
                if not other_window.isVisible():
                    continue

                other_geo = other_window.geometry()
                if new_geo.intersects(other_geo):
                    overlap = new_geo.intersected(other_geo)
                    if overlap.width() < overlap.height():
                        if new_geo.center().x() < other_geo.center().x():
                            new_geo.moveLeft(other_geo.left() - new_geo.width())
                        else:
                            new_geo.moveLeft(other_geo.right())
                    else:
                        if new_geo.center().y() < other_geo.center().y():
                            new_geo.moveTop(other_geo.top() - new_geo.height())
                        else:
                            new_geo.moveTop(other_geo.bottom())
                    moved = True
            if not moved:
                break

        screen = self.screen().availableGeometry()
        if new_geo.left() < screen.left():
            new_geo.moveLeft(screen.left())
        if new_geo.right() > screen.right():
            new_geo.moveRight(screen.right())
        if new_geo.top() < screen.top():
            new_geo.moveTop(screen.top())
        if new_geo.bottom() > screen.bottom():
            new_geo.moveBottom(screen.bottom())

        return new_geo.topLeft()

    def try_magnet(self):
        self.magnet_targets = []
        threshold = 35

        main_window = self.manager.get_main_window()
        if main_window and not getattr(main_window, "is_dock_hidden", False):
            main_geo = main_window.geometry()
            note_geo = self.geometry()

            if abs(note_geo.top() - main_geo.bottom()) < threshold and self._is_horizontal_overlap(main_geo, note_geo):
                offset_x = note_geo.left() - main_geo.left()
                self.move(main_geo.left() + offset_x, main_geo.bottom())
                self.magnet_targets.append(("main", "bottom"))
                self.magnet_offset = (offset_x, 0)
                self.is_magnet = True
                return

            if abs(note_geo.bottom() - main_geo.top()) < threshold and self._is_horizontal_overlap(main_geo, note_geo):
                offset_x = note_geo.left() - main_geo.left()
                self.move(main_geo.left() + offset_x, main_geo.top() - note_geo.height())
                self.magnet_targets.append(("main", "top"))
                self.magnet_offset = (offset_x, 0)
                self.is_magnet = True
                return

            if abs(note_geo.left() - main_geo.right()) < threshold and self._is_vertical_overlap(main_geo, note_geo):
                offset_y = note_geo.top() - main_geo.top()
                self.move(main_geo.right(), main_geo.top() + offset_y)
                self.magnet_targets.append(("main", "right"))
                self.magnet_offset = (0, offset_y)
                self.is_magnet = True
                return

            if abs(note_geo.right() - main_geo.left()) < threshold and self._is_vertical_overlap(main_geo, note_geo):
                offset_y = note_geo.top() - main_geo.top()
                self.move(main_geo.left() - note_geo.width(), main_geo.top() + offset_y)
                self.magnet_targets.append(("main", "left"))
                self.magnet_offset = (0, offset_y)
                self.is_magnet = True
                return

        for other_id, other_window in self.manager.note_windows.items():
            if other_id == self.note_id:
                continue

            other_geo = other_window.geometry()
            note_geo = self.geometry()

            if abs(note_geo.top() - other_geo.bottom()) < threshold and self._is_horizontal_overlap(
                other_geo, note_geo
            ):
                aligned_x = other_geo.left()
                self.move(aligned_x, other_geo.bottom())
                self.magnet_targets.append((other_id, "bottom"))
                self.is_magnet = True
                return

            if abs(note_geo.bottom() - other_geo.top()) < threshold and self._is_horizontal_overlap(
                other_geo, note_geo
            ):
                aligned_x = other_geo.left()
                self.move(aligned_x, other_geo.top() - note_geo.height())
                self.magnet_targets.append((other_id, "top"))
                self.is_magnet = True
                return

            if abs(note_geo.left() - other_geo.right()) < threshold and self._is_vertical_overlap(other_geo, note_geo):
                aligned_y = other_geo.top()
                self.move(other_geo.right(), aligned_y)
                self.magnet_targets.append((other_id, "right"))
                self.is_magnet = True
                return

            if abs(note_geo.right() - other_geo.left()) < threshold and self._is_vertical_overlap(other_geo, note_geo):
                aligned_y = other_geo.top()
                self.move(other_geo.left() - note_geo.width(), aligned_y)
                self.magnet_targets.append((other_id, "left"))
                self.is_magnet = True
                return

    _is_horizontal_overlap = staticmethod(is_horizontal_overlap)
    _is_vertical_overlap = staticmethod(is_vertical_overlap)
