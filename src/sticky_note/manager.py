import json
import uuid
from pathlib import Path

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QGuiApplication

MAX_NOTES = 500

from src.sticky_note.panel import StickyNotePanel
from src.sticky_note.window import StickyNoteWindow
from src.utils.geometry import is_horizontal_overlap, is_vertical_overlap
from src.utils.logger import get_logger

logger = get_logger("StickyNoteManager")
MAX_NOTE_TEXT = 10000


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
        self.main_window = window

    def get_main_window(self):
        return self.main_window

    def get_panel(self):
        self.panel = StickyNotePanel(self.settings, self)
        return self.panel

    def load_notes(self):
        if self.notes_file and self.notes_file.exists():
            try:
                with open(self.notes_file, encoding='utf-8') as f:
                    data = json.load(f)
                    notes = data.get('notes', [])
                    self.notes = notes[:MAX_NOTES]
                    for n in self.notes:
                        if isinstance(n, dict) and 'text' in n:
                            n['text'] = n['text'][:MAX_NOTE_TEXT]
            except Exception as e:
                logger.warning("Failed to load notes from %s: %s", self.notes_file, e)
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

        self.notes = notes_data[:MAX_NOTES]
        for n in self.notes:
            if isinstance(n, dict) and 'text' in n:
                n['text'] = n['text'][:MAX_NOTE_TEXT]
        Path(self.notes_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.notes_file, 'w', encoding='utf-8') as f:
            json.dump({'notes': self.notes}, f, indent=2, ensure_ascii=False)

    def create_note(self, note_data=None):
        if len(self.notes) >= MAX_NOTES:
            logger.warning("Max notes reached (%d), cannot create more", MAX_NOTES)
            return None
        if note_data:
            if 'id' not in note_data:
                return None
            note_id = note_data.get('id')
            if not note_id or not isinstance(note_id, str):
                return None
            text = note_data.get('text', '')[:MAX_NOTE_TEXT]
            color = note_data.get('color', 'yellow')
            x = note_data.get('x', 100)
            y = note_data.get('y', 100)
            if not any(isinstance(n, dict) and n.get('id') == note_id for n in self.notes):
                self.notes.append(note_data)
                self.save_notes()
        else:
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

        if note_id in self.note_windows:
            self.note_windows[note_id].close()
            del self.note_windows[note_id]

        window = StickyNoteWindow(note_id, text, color, x, y, self)
        self.note_windows[note_id] = window
        window.is_magnet = True

        self.snap_to_main_window(window)

        if self.panel:
            QTimer.singleShot(100, self.panel.load_note_cards)

        return window

    def delete_note(self, note_id):
        if note_id in self.note_windows:
            window = self.note_windows[note_id]
            window.deleteLater()
            del self.note_windows[note_id]

        self.notes = [n for n in self.notes if isinstance(n, dict) and n.get('id') != note_id]
        self.save_notes()

        if hasattr(self, 'panel') and self.panel:
            QTimer.singleShot(100, self.panel.load_note_cards)

    def update_note_content(self, note_id, text):
        text = text[:MAX_NOTE_TEXT]
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
        if len(self.notes) >= MAX_NOTES:
            logger.warning("Max notes reached (%d), cannot create more", MAX_NOTES)
            return None
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
        if self.panel:
            self.panel.refresh_card_color(note_id, color)

    def show_all_notes(self):
        valid_notes = [n for n in self.notes if isinstance(n, dict) and 'id' in n]
        for note_data in valid_notes:
            note_id = note_data.get('id')
            if note_id and note_id not in self.note_windows:
                self.create_note(note_data)

        if not valid_notes:
            note_data = {
                'id': str(uuid.uuid4()),
                'text': '',
                'color': 'yellow',
                'x': 200,
                'y': 200
            }
            self.create_note(note_data)

        if self.panel:
            QTimer.singleShot(200, self.panel.load_note_cards)

    def show_note_by_id(self, note_id):
        note_data = None
        for note in self.notes:
            if isinstance(note, dict) and note.get('id') == note_id:
                note_data = note.copy()
                break

        if note_data:
            if note_id in self.note_windows:
                self.note_windows[note_id].show()
                self.note_windows[note_id].activateWindow()
            else:
                self.create_note(note_data)

    def toggle_note(self, note_id):
        if note_id in self.note_windows:
            if self.note_windows[note_id].isVisible():
                self.note_windows[note_id].hide()
            else:
                self.note_windows[note_id].show()
                self.note_windows[note_id].activateWindow()
        else:
            note_data = None
            for note in self.notes:
                if isinstance(note, dict) and note.get('id') == note_id:
                    note_data = note.copy()
                    break
            if note_data:
                self.create_note(note_data)

    def snap_to_main_window(self, window):
        main_window = self.get_main_window()
        is_dock_hidden = getattr(main_window, 'is_dock_hidden', False) if main_window else False
        if not main_window or (not main_window.isVisible() and is_dock_hidden):
            window.show()
            return

        main_geo = main_window.geometry()
        note_w = window.width()
        note_h = window.height()

        screen = QGuiApplication.primaryScreen()
        if not screen:
            window.show()
            return

        screen_geo = screen.availableGeometry()

        base_x = main_geo.right() + 5
        base_y = main_geo.top()

        occupied_positions = []
        for other_id, other_window in self.note_windows.items():
            if other_id != window.note_id and other_window.isVisible():
                occupied_positions.append(other_window.geometry())

        best_x = base_x
        best_y = base_y

        if best_x + note_w > screen_geo.right():
            best_x = main_geo.left() - note_w - 5

        max_attempts = 20
        for attempt in range(max_attempts):
            test_rect = QRect(best_x, best_y, note_w, note_h)

            overlap = False
            for other_rect in occupied_positions:
                if test_rect.intersects(other_rect):
                    overlap = True
                    best_y = other_rect.bottom() + 5
                    break

            if not overlap:
                break

            if best_y + note_h > screen_geo.bottom():
                best_y = base_y
                best_x += note_w + 5
                if best_x + note_w > screen_geo.right():
                    best_x = base_x
                    break

        if best_y + note_h > screen_geo.bottom():
            best_y = screen_geo.bottom() - note_h - 5
        if best_y < screen_geo.top():
            best_y = screen_geo.top() + 5

        if best_x > main_geo.center().x():
            best_x = main_geo.right() + 5
        else:
            best_x = main_geo.left() - note_w - 5

        window.move(best_x, best_y)
        is_right = best_x > main_geo.center().x()
        window.magnet_targets = [('main', 'right' if is_right else 'left')]
        offset_y = best_y - main_geo.top()
        window.magnet_offset = (0, offset_y)
        window.is_magnet = True
        window.show()

    def hide_magnet_notes(self):
        to_hide = set()

        for note_id, window in self.note_windows.items():
            if not isinstance(note_id, str):
                continue
            if window.is_magnet:
                to_hide.add(note_id)
            for target in window.magnet_targets:
                if isinstance(target, tuple) and len(target) > 0:
                    target_id = target[0]
                    if target_id == 'main':
                        to_hide.add(note_id)
                        break
                    if isinstance(target_id, str) and target_id in to_hide:
                        to_hide.add(note_id)
                        break

        changed = True
        while changed:
            changed = False
            for note_id, window in self.note_windows.items():
                if not isinstance(note_id, str) or note_id in to_hide:
                    continue
                for target in window.magnet_targets:
                    if isinstance(target, tuple) and len(target) > 0:
                        target_id = target[0]
                        if isinstance(target_id, str) and target_id in to_hide:
                            to_hide.add(note_id)
                            changed = True
                            break

        for note_id in to_hide:
            if note_id in self.note_windows:
                self.note_windows[note_id].hide()

    def show_magnet_notes(self):
        for window in self.note_windows.values():
            window.show()

    def update_magnet_notes_position(self):
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

    _is_horizontal_overlap = staticmethod(is_horizontal_overlap)
    _is_vertical_overlap = staticmethod(is_vertical_overlap)
