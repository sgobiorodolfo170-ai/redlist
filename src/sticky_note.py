import json
import uuid
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.theme import COLORS, NOTE_COLORS


class StickyNoteManager:
    def __init__(self, settings):
        self.settings = settings
        self.notes = []
        self.note_windows = {}
        self.panel = None
        self.main_window = None
        self.notes_file = None
        QTimer.singleShot(0, self._delayed_load)

    def _delayed_load(self):
        self.notes_file = self._get_notes_file_path()
        self.load_notes()
        if self.panel:
            self.panel.load_note_cards()

    def _get_notes_file_path(self):
        path = self.settings.get_notes_path()
        Path(path).mkdir(parents=True, exist_ok=True)
        return Path(path) / 'notes.json'

    def refresh_path(self):
        for note_id in list(self.note_windows.keys()):
            self.note_windows[note_id].close()
        self.note_windows.clear()
        self.notes_file = self._get_notes_file_path()
        self.load_notes()
        if self.panel:
            self.panel.load_note_cards()

    def cleanup(self):
        for note_id in list(self.note_windows.keys()):
            self.note_windows[note_id].close()
        self.note_windows.clear()

    def set_main_window(self, window):
        """设置主窗口引用"""
        self.main_window = window

    def get_main_window(self):
        """获取主窗口"""
        return self.main_window

    def get_panel(self):
        self.panel = StickyNotePanel(self.settings, self)
        return self.panel

    def load_notes(self):
        if self.notes_file and self.notes_file.exists():
            try:
                with open(self.notes_file, encoding='utf-8') as f:
                    data = json.load(f)
                    self.notes = data.get('notes', [])
            except Exception:
                self.notes = []
        else:
            self.notes = []

    def save_notes(self):
        if not self.notes_file:
            return
        notes_data = []
        saved_ids = set()

        for note_id, window in self.note_windows.items():
            if not isinstance(note_id, str):
                continue
            note_data = {
                'id': note_id,
                'text': window.text_edit.toPlainText(),
                'color': window.color,
                'x': window.x(),
                'y': window.y()
            }
            notes_data.append(note_data)
            saved_ids.add(note_id)

        for note in self.notes:
            if not isinstance(note, dict):
                continue
            note_id = note.get('id')
            if note_id and note_id not in saved_ids:
                notes_data.append(note)
                saved_ids.add(note_id)

        self.notes = notes_data
        Path(self.notes_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.notes_file, 'w', encoding='utf-8') as f:
            json.dump({'notes': notes_data}, f, indent=2, ensure_ascii=False)

    def create_note(self, note_data=None):
        if note_data:
            if 'id' not in note_data:
                return None
            note_id = note_data.get('id')
            if not note_id or not isinstance(note_id, str):
                return None
            text = note_data.get('text', '')
            color = note_data.get('color', 'yellow')
            x = note_data.get('x', 100)
            y = note_data.get('y', 100)
            # 确保note_data在notes列表中
            if not any(isinstance(n, dict) and n.get('id') == note_id for n in self.notes):
                self.notes.append(note_data)
                self.save_notes()
        else:
            note_id = str(uuid.uuid4())
            text = ''
            color = 'yellow'
            x = 200
            y = 200
            # 添加到 notes 列表
            note_data = {
                'id': note_id,
                'text': text,
                'color': color
            }
            self.notes.append(note_data)
            self.save_notes()

        # 如果窗口已存在，先关闭
        if note_id in self.note_windows:
            self.note_windows[note_id].close()
            del self.note_windows[note_id]

        window = StickyNoteWindow(note_id, text, color, x, y, self)
        self.note_windows[note_id] = window
        window.is_magnet = True  # 新建的便利贴默认吸附

        # 自动吸附到主窗口边缘
        self.snap_to_main_window(window)

        # 刷新面板卡片
        if self.panel:
            QTimer.singleShot(100, self.panel.load_note_cards)

        return window

    def delete_note(self, note_id):
        # 如果窗口存在，先关闭它
        if note_id in self.note_windows:
            window = self.note_windows[note_id]
            window.deleteLater()  # 安全删除
            del self.note_windows[note_id]

        # 从数据中删除
        self.notes = [n for n in self.notes if isinstance(n, dict) and n.get('id') != note_id]
        self.save_notes()

        # 刷新面板中的卡片列表
        if hasattr(self, 'panel') and self.panel:
            QTimer.singleShot(100, self.panel.load_note_cards)

    def update_note_content(self, note_id, text):
        for note in self.notes:
            if isinstance(note, dict) and note.get('id') == note_id:
                note['text'] = text
                break
        else:
            self.notes.append({'id': note_id, 'text': text, 'color': 'yellow'})
        self.save_notes()
        if self.panel:
            self.panel.refresh_card_text(note_id, text)

    def create_sticky_note(self):
        """创建一个新的便利贴窗口并返回"""
        note_id = str(uuid.uuid4())
        text = ''
        color = 'yellow'
        x = 200
        y = 200

        note_data = {
            'id': note_id,
            'text': text,
            'color': color
        }
        self.notes.append(note_data)
        self.save_notes()

        window = StickyNoteWindow(note_id, text, color, x, y, self)
        self.note_windows[note_id] = window
        window.is_magnet = True

        self.snap_to_main_window(window)

        if self.panel:
            QTimer.singleShot(100, self.panel.load_note_cards)

        return window

    def update_note_color(self, note_id, color):
        for note in self.notes:
            if isinstance(note, dict) and note.get('id') == note_id:
                note['color'] = color
                break
        self.save_notes()
        # 刷新面板卡片颜色
        if self.panel:
            self.panel.refresh_card_color(note_id, color)

    def show_all_notes(self):
        # 显示所有保存的便签
        valid_notes = [n for n in self.notes if isinstance(n, dict) and 'id' in n]
        for note_data in valid_notes:
            note_id = note_data.get('id')
            if note_id and note_id not in self.note_windows:
                self.create_note(note_data)

        # 如果没有有效的便签，创建一个新的
        if not valid_notes:
            note_data = {
                'id': str(uuid.uuid4()),
                'text': '',
                'color': 'yellow',
                'x': 200,
                'y': 200
            }
            self.create_note(note_data)

        # 刷新面板卡片
        if self.panel:
            QTimer.singleShot(200, self.panel.load_note_cards)

    def show_note_by_id(self, note_id):
        """根据ID显示指定便签"""
        # 先查找是否存在
        note_data = None
        for note in self.notes:
            if isinstance(note, dict) and note.get('id') == note_id:
                note_data = note.copy()
                break

        if note_data:
            # 如果窗口已打开，直接显示
            if note_id in self.note_windows:
                self.note_windows[note_id].show()
                self.note_windows[note_id].activateWindow()
            else:
                # 创建新窗口
                self.create_note(note_data)

    def toggle_note(self, note_id):
        """切换便签显示/隐藏"""
        if note_id in self.note_windows:
            # 如果窗口可见，则隐藏
            if self.note_windows[note_id].isVisible():
                self.note_windows[note_id].hide()
            else:
                # 否则显示
                self.note_windows[note_id].show()
                self.note_windows[note_id].activateWindow()
        else:
            # 窗口不存在，创建并显示
            note_data = None
            for note in self.notes:
                if isinstance(note, dict) and note.get('id') == note_id:
                    note_data = note.copy()
                    break
            if note_data:
                self.create_note(note_data)

    def snap_to_main_window(self, window):
        """将便签吸附到主窗口边缘，自动对齐并避免重叠"""
        main_window = self.get_main_window()
        is_dock_hidden = getattr(main_window, 'is_dock_hidden', False) if main_window else False
        if not main_window or (not main_window.isVisible() and is_dock_hidden):
            window.show()
            return

        main_geo = main_window.geometry()
        note_w = window.width()
        note_h = window.height()

        # 计算可用位置（从主窗口右侧开始，向下排列）
        from PyQt6.QtCore import QRect
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if not screen:
            window.show()
            return

        screen_geo = screen.availableGeometry()

        # 尝试在主窗口右侧找到不重叠的位置
        base_x = main_geo.right() + 5
        base_y = main_geo.top()

        # 收集所有已显示的便签位置
        occupied_positions = []
        for other_id, other_window in self.note_windows.items():
            if other_id != window.note_id and other_window.isVisible():
                occupied_positions.append(other_window.geometry())

        # 尝试找到不重叠的位置（垂直排列，自动对齐到主窗口顶部）
        best_x = base_x
        best_y = base_y

        # 如果右侧超出屏幕，尝试左侧
        if best_x + note_w > screen_geo.right():
            best_x = main_geo.left() - note_w - 5

        # 垂直方向找位置（与主窗口左对齐）
        max_attempts = 20
        for attempt in range(max_attempts):
            test_rect = QRect(best_x, best_y, note_w, note_h)

            # 检查是否与任何便签重叠
            overlap = False
            for other_rect in occupied_positions:
                if test_rect.intersects(other_rect):
                    overlap = True
                    # 向下移动一个便签高度+间距
                    best_y = other_rect.bottom() + 5
                    break

            if not overlap:
                break

            # 如果超出屏幕底部，尝试右侧的下一列
            if best_y + note_h > screen_geo.bottom():
                best_y = base_y
                best_x += note_w + 5
                # 如果新列也超出屏幕，回到第一列但重叠显示
                if best_x + note_w > screen_geo.right():
                    best_x = base_x
                    break

        # 确保不超出屏幕边界
        if best_y + note_h > screen_geo.bottom():
            best_y = screen_geo.bottom() - note_h - 5
        if best_y < screen_geo.top():
            best_y = screen_geo.top() + 5

        # 对齐到主窗口的左边缘（如果是右侧吸附）
        if best_x > main_geo.center().x():
            best_x = main_geo.right() + 5  # 右侧吸附，X对齐
        else:
            best_x = main_geo.left() - note_w - 5  # 左侧吸附，X对齐

        window.move(best_x, best_y)
        is_right = best_x > main_geo.center().x()
        window.magnet_targets = [('main', 'right' if is_right else 'left')]
        offset_y = best_y - main_geo.top()
        window.magnet_offset = (0, offset_y)
        window.is_magnet = True
        window.show()

    def hide_magnet_notes(self):
        """隐藏所有吸附的便利贴"""
        # 收集所有需要隐藏的便签ID（包括直接吸附和间接吸附）
        to_hide = set()

        for note_id, window in self.note_windows.items():
            if not isinstance(note_id, str):
                continue
            # 直接吸附到主窗口的
            if window.is_magnet:
                to_hide.add(note_id)
            # 磁吸到主窗口的
            for target in window.magnet_targets:
                if isinstance(target, tuple) and len(target) > 0:
                    target_id = target[0]
                    if target_id == 'main':
                        to_hide.add(note_id)
                        break
                    # 检查 target_id 是否在 to_hide 中
                    if isinstance(target_id, str) and target_id in to_hide:
                        to_hide.add(note_id)
                        break

        # 收集连接到已隐藏便签的便签（间接吸附）
        changed = True
        while changed:
            changed = False
            for note_id, window in self.note_windows.items():
                if not isinstance(note_id, str) or note_id in to_hide:
                    continue
                # 检查是否连接到已隐藏的便签
                for target in window.magnet_targets:
                    if isinstance(target, tuple) and len(target) > 0:
                        target_id = target[0]
                        if isinstance(target_id, str) and target_id in to_hide:
                            to_hide.add(note_id)
                            changed = True
                            break

        # 执行隐藏
        for note_id in to_hide:
            if note_id in self.note_windows:
                self.note_windows[note_id].hide()

    def show_magnet_notes(self):
        """显示所有吸附的便利贴"""
        for window in self.note_windows.values():
            window.show()

    def update_magnet_notes_position(self):
        """更新所有吸附到主窗口的便利贴位置，并主动吸附附近的便利贴"""
        main_window = self.get_main_window()
        if not main_window:
            return

        main_geo = main_window.geometry()
        threshold = 35

        for note_id, window in self.note_windows.items():
            if not hasattr(window, 'magnet_targets'):
                window.magnet_targets = []

            if not window.isVisible():
                continue

            has_main_target = False
            for target in window.magnet_targets:
                if isinstance(target, tuple) and len(target) >= 2:
                    target_id, position = target[0], target[1]
                    if target_id == 'main':
                        has_main_target = True
                        if not hasattr(window, 'magnet_offset') or window.magnet_offset is None:
                            note_geo = window.geometry()
                            if position == 'right':
                                window.magnet_offset = (0, note_geo.top() - main_geo.top())
                            elif position == 'left':
                                window.magnet_offset = (0, note_geo.top() - main_geo.top())
                            elif position == 'top':
                                window.magnet_offset = (note_geo.left() - main_geo.left(), 0)
                            elif position == 'bottom':
                                window.magnet_offset = (note_geo.left() - main_geo.left(), 0)

                        offset = window.magnet_offset
                        if position == 'right':
                            window.move(main_geo.right() + offset[0], main_geo.top() + offset[1])
                        elif position == 'left':
                            window.move(main_geo.left() - window.width() + offset[0], main_geo.top() + offset[1])
                        elif position == 'top':
                            window.move(main_geo.left() + offset[0], main_geo.top() - window.height() + offset[1])
                        elif position == 'bottom':
                            window.move(main_geo.left() + offset[0], main_geo.bottom() + offset[1])
                        break

            if not has_main_target:
                note_geo = window.geometry()
                dist_right = abs(note_geo.left() - main_geo.right())
                dist_left = abs(note_geo.right() - main_geo.left())
                dist_bottom = abs(note_geo.top() - main_geo.bottom())
                dist_top = abs(note_geo.bottom() - main_geo.top())

                if dist_right < threshold and self._is_vertical_overlap(main_geo, note_geo):
                    offset_y = note_geo.top() - main_geo.top()
                    window.move(main_geo.right(), main_geo.top() + offset_y)
                    window.magnet_targets = [('main', 'right')]
                    window.magnet_offset = (0, offset_y)
                    window.is_magnet = True

                elif dist_left < threshold and self._is_vertical_overlap(main_geo, note_geo):
                    offset_y = note_geo.top() - main_geo.top()
                    window.move(main_geo.left() - note_geo.width(), main_geo.top() + offset_y)
                    window.magnet_targets = [('main', 'left')]
                    window.magnet_offset = (0, offset_y)
                    window.is_magnet = True

                elif dist_bottom < threshold and self._is_horizontal_overlap(main_geo, note_geo):
                    offset_x = note_geo.left() - main_geo.left()
                    window.move(main_geo.left() + offset_x, main_geo.bottom())
                    window.magnet_targets = [('main', 'bottom')]
                    window.magnet_offset = (offset_x, 0)
                    window.is_magnet = True

                elif dist_top < threshold and self._is_horizontal_overlap(main_geo, note_geo):
                    offset_x = note_geo.left() - main_geo.left()
                    window.move(main_geo.left() + offset_x, main_geo.top() - note_geo.height())
                    window.magnet_targets = [('main', 'top')]
                    window.magnet_offset = (offset_x, 0)
                    window.is_magnet = True

    @staticmethod
    def _is_horizontal_overlap(geo1, geo2):
        """检查两个矩形是否水平重叠"""
        return not (geo1.right() < geo2.left() or geo1.left() > geo2.right())

    @staticmethod
    def _is_vertical_overlap(geo1, geo2):
        """检查两个矩形是否垂直重叠"""
        return not (geo1.bottom() < geo2.top() or geo1.top() > geo2.bottom())


class StickyNotePanel(QWidget):

    def __init__(self, settings, manager):
        super().__init__()
        self.settings = settings
        self.manager = manager
        self.card_editors = {}
        self.card_frames = {}

        self.init_ui()

    def init_ui(self):
        # 设置面板背景为白色
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)

        # 标题
        header = QLabel("便利贴")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: black;
            padding: 8px 0;
        """)
        layout.addWidget(header)

        # 滚动区域显示便签卡片
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

        # 按钮区域
        btn_layout = QHBoxLayout()

        # 新建按钮
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

        # 显示全部按钮
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
        """加载便签卡片"""
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
        """创建单个便签卡片"""
        # 确保 note 是有效的字典且有 id
        if not isinstance(note, dict) or 'id' not in note:
            return

        card = QFrame()
        # 卡片高度保持两行文本高度（约50px）
        card.setFixedHeight(50)
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        # 使用与便签窗口相同的颜色
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
        """刷新单个卡片的颜色"""
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
        """刷新单个卡片的文本内容"""
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
        """卡片点击事件：单击显示/隐藏"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.manager.toggle_note(note_id)

    def on_card_double_click(self, event, note_id):
        """卡片双击事件：删除确认"""
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
        """新建便签"""
        self.manager.create_note()
        # 延迟刷新卡片
        QTimer.singleShot(300, self.load_note_cards)

    def toggle_all_notes(self):
        """显示/隐藏所有便签（切换）"""
        manager_notes = getattr(self.manager, 'notes', [])
        valid_notes = [n for n in manager_notes if isinstance(n, dict) and isinstance(n.get('id'), str)]
        note_ids = [note['id'] for note in valid_notes]

        # 检查当前是否有任何可见的便签窗口
        any_visible = False
        for nid in note_ids:
            if nid in self.manager.note_windows:
                if self.manager.note_windows[nid].isVisible():
                    any_visible = True
                    break

        if any_visible:
            # 隐藏所有便签
            for window in self.manager.note_windows.values():
                window.hide()
            self.show_btn.setText("显示全部")
        else:
            # 显示所有便签
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
                # 没有便签，创建一个新的
                self.manager.create_note()
                QTimer.singleShot(300, self.load_note_cards)
            self.show_btn.setText("隐藏全部")

    def delete_note(self, note_id):
        """删除便签"""
        self.manager.delete_note(note_id)
        # 延迟刷新卡片
        QTimer.singleShot(100, self.load_note_cards)

    def refresh_cards(self):
        """刷新卡片"""
        self.load_note_cards()


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
        bg_color = NOTE_COLORS.get(self.color, NOTE_COLORS['yellow'])

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # 开放式文本输入（无边框样式）
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
        # 禁用text_edit的右键菜单，让父窗口处理
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.text_edit.textChanged.connect(self.on_text_changed)
        # 安装事件过滤器以捕获双击事件
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
        """右键菜单：复制粘贴"""
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

        # 复制
        copy_action = menu.addAction("复制")
        copy_action.triggered.connect(lambda: self.text_edit.copy())

        # 粘贴
        paste_action = menu.addAction("粘贴")
        paste_action.triggered.connect(lambda: self.text_edit.paste())

        menu.exec(event.globalPos())

    def mouseDoubleClickEvent(self, event):
        """双击换色"""
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
        """设置便签颜色"""
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
        """设置便签内容"""
        self.text_edit.setPlainText(text)
        self.manager.update_note_content(self.note_id, text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            # 拖拽时暂时解除磁贴
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
            # 释放时尝试磁吸
            self.try_magnet()

    def eventFilter(self, obj, event):
        """事件过滤器，处理子控件的鼠标事件"""
        # 处理text_edit的双击事件（用于切换颜色）
        if hasattr(self, 'text_edit') and obj == self.text_edit:
            if event.type() == event.Type.MouseButtonDblClick:
                self.mouseDoubleClickEvent(event)
                return True
            # 处理text_edit的右键菜单
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
        """避免与其他便签重叠，返回调整后的位置"""
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
        """尝试磁吸到其他便签或主窗口"""
        self.magnet_targets = []
        threshold = 35

        main_window = self.manager.get_main_window()
        if main_window and not getattr(main_window, 'is_dock_hidden', False):
            main_geo = main_window.geometry()
            note_geo = self.geometry()

            if abs(note_geo.top() - main_geo.bottom()) < threshold and self._is_horizontal_overlap(main_geo, note_geo):
                offset_x = note_geo.left() - main_geo.left()
                self.move(main_geo.left() + offset_x, main_geo.bottom())
                self.magnet_targets.append(('main', 'bottom'))
                self.magnet_offset = (offset_x, 0)
                self.is_magnet = True
                return

            if abs(note_geo.bottom() - main_geo.top()) < threshold and self._is_horizontal_overlap(main_geo, note_geo):
                offset_x = note_geo.left() - main_geo.left()
                self.move(main_geo.left() + offset_x, main_geo.top() - note_geo.height())
                self.magnet_targets.append(('main', 'top'))
                self.magnet_offset = (offset_x, 0)
                self.is_magnet = True
                return

            if abs(note_geo.left() - main_geo.right()) < threshold and self._is_vertical_overlap(main_geo, note_geo):
                offset_y = note_geo.top() - main_geo.top()
                self.move(main_geo.right(), main_geo.top() + offset_y)
                self.magnet_targets.append(('main', 'right'))
                self.magnet_offset = (0, offset_y)
                self.is_magnet = True
                return

            if abs(note_geo.right() - main_geo.left()) < threshold and self._is_vertical_overlap(main_geo, note_geo):
                offset_y = note_geo.top() - main_geo.top()
                self.move(main_geo.left() - note_geo.width(), main_geo.top() + offset_y)
                self.magnet_targets.append(('main', 'left'))
                self.magnet_offset = (0, offset_y)
                self.is_magnet = True
                return

        for other_id, other_window in self.manager.note_windows.items():
            if other_id == self.note_id:
                continue

            other_geo = other_window.geometry()
            note_geo = self.geometry()

            if (abs(note_geo.top() - other_geo.bottom()) < threshold
                    and self._is_horizontal_overlap(other_geo, note_geo)):
                aligned_x = other_geo.left()
                self.move(aligned_x, other_geo.bottom())
                self.magnet_targets.append((other_id, 'bottom'))
                self.is_magnet = True
                return

            if (abs(note_geo.bottom() - other_geo.top()) < threshold
                    and self._is_horizontal_overlap(other_geo, note_geo)):
                aligned_x = other_geo.left()
                self.move(aligned_x, other_geo.top() - note_geo.height())
                self.magnet_targets.append((other_id, 'top'))
                self.is_magnet = True
                return

            if abs(note_geo.left() - other_geo.right()) < threshold and self._is_vertical_overlap(other_geo, note_geo):
                aligned_y = other_geo.top()
                self.move(other_geo.right(), aligned_y)
                self.magnet_targets.append((other_id, 'right'))
                self.is_magnet = True
                return

            if abs(note_geo.right() - other_geo.left()) < threshold and self._is_vertical_overlap(other_geo, note_geo):
                aligned_y = other_geo.top()
                self.move(other_geo.left() - note_geo.width(), aligned_y)
                self.magnet_targets.append((other_id, 'left'))
                self.is_magnet = True
                return

    def _is_horizontal_overlap(self, geo1, geo2):
        """检查两个矩形水平方向是否重叠"""
        return not (geo1.right() < geo2.left() or geo1.left() > geo2.right())

    def _is_vertical_overlap(self, geo1, geo2):
        """检查两个矩形垂直方向是否重叠"""
        return not (geo1.bottom() < geo2.top() or geo1.top() > geo2.bottom())
