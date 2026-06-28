from typing import Any, List, Tuple

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QWidget


class _BaseMaskOverlay(QWidget):
    """Base overlay with shared drag/resize/paint/toolbar logic."""

    screenshot_signal = pyqtSignal()

    def __init__(self, sticky_manager=None):
        super().__init__()
        self.text_items: List[Any] = []
        self.sticky_manager = sticky_manager
        self.toolbar = None
        self.screenshot_rect = QRect()
        self.dragging = False
        self.resizing = False
        self.drag_position = QPoint()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # --- hooks for subclasses ---

    def _paint_border_color(self) -> QColor:
        return QColor(255, 0, 0)

    def _paint_text_bg_color(self) -> QColor:
        return QColor(255, 255, 255, 255)

    def _paint_display_text(self) -> str:
        return ""

    def _toolbar_buttons(self) -> List[Tuple[str, str, bool]]:
        return []

    def _on_close(self):
        pass

    def _sticky_target_text(self) -> str:
        return ""

    def _set_text_items(self, items, screenshot_rect):
        self.text_items = items
        self.screenshot_rect = screenshot_rect

    # --- shared set_texts ---

    def set_texts(self, items, screenshot_rect):
        self._set_text_items(items, screenshot_rect)

        screens = QGuiApplication.screens()
        if screens:
            total_geometry = screens[0].geometry()
            for screen in screens[1:]:
                total_geometry = total_geometry.united(screen.geometry())
            self.setGeometry(total_geometry)

        self._create_toolbar()
        self.update()
        self.show()
        self.setFocus()

    # --- shared toolbar ---

    def _create_toolbar(self):
        if self.toolbar:
            self.toolbar.close()

        self.toolbar = QWidget()
        self.toolbar.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.toolbar.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.toolbar.setFixedHeight(40)

        self.toolbar.setStyleSheet("""
            QWidget {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F8F9FA);
                border-radius: 10px;
                border: 1px solid #DEE2E6;
            }
        """)

        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        for label, slot, is_primary in self._toolbar_buttons():
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if is_primary:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #28A745;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 14px;
                        font-size: 13px;
                        color: white;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #218838;
                    }
                    QPushButton:pressed {
                        background-color: #1E7E34;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F8F9FA;
                        border: 1px solid #DEE2E6;
                        border-radius: 6px;
                        padding: 6px 14px;
                        font-size: 13px;
                        color: #495057;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #E9ECEF;
                        border-color: #ADB5BD;
                    }
                    QPushButton:pressed {
                        background-color: #DEE2E6;
                    }
                """)
            btn.clicked.connect(getattr(self, slot))
            layout.addWidget(btn)

        toolbar_width = layout.sizeHint().width()
        self.toolbar.setFixedWidth(toolbar_width + 20)

        toolbar_x = self.screenshot_rect.right() - toolbar_width - 20
        toolbar_y = self.screenshot_rect.bottom() + 5
        self.toolbar.move(toolbar_x, toolbar_y)
        self.toolbar.show()

    # --- shared paint ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QBrush(QColor(0, 0, 0, 120)))

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.screenshot_rect, QBrush(QColor(0, 0, 0, 0)))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        pen = QPen(self._paint_border_color(), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawRect(self.screenshot_rect.adjusted(0, 0, -1, -1))

        text_box_rect = self.screenshot_rect.adjusted(1, 1, -1, -1)
        painter.fillRect(text_box_rect, QBrush(self._paint_text_bg_color()))

        pad = int(max(3, min(10, self.screenshot_rect.height() * 0.08)))
        text_rect = text_box_rect.adjusted(pad, pad, -pad, -pad)

        display_text = self._paint_display_text()
        if text_rect.width() > 0 and text_rect.height() > 0 and display_text:
            font_size = self._fit_font_size(text_rect, display_text)
            painter.setPen(QColor(50, 50, 50))
            font = QFont("Microsoft YaHei", font_size)
            painter.setFont(font)
            painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, display_text)

    # --- shared helpers ---

    def _fit_font_size(self, rect, text):
        if not text:
            return 12

        font = QFont("Microsoft YaHei")
        for size in range(22, 7, -1):
            font.setPointSize(size)
            fm = QFontMetrics(font)
            text_rect = fm.boundingRect(rect, Qt.TextFlag.TextWordWrap, text)
            if text_rect.height() <= rect.height() and text_rect.width() <= rect.width():
                return size
        return 8

    # --- shared mouse handling ---

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.close()
            if self.toolbar:
                self.toolbar.close()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            margin = 10
            rect = self.screenshot_rect

            if pos.x() >= rect.right() - margin and pos.y() >= rect.bottom() - margin:
                self.resizing = True
                self.drag_position = pos
            elif rect.contains(pos):
                self.dragging = True
                self.drag_position = pos

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.pos() - self.drag_position
            self.screenshot_rect.translate(delta)
            self.drag_position = event.pos()
            self.update()
            self._update_toolbar_position()
        elif self.resizing:
            delta = event.pos() - self.drag_position
            self.screenshot_rect.setRight(self.screenshot_rect.right() + delta.x())
            self.screenshot_rect.setBottom(self.screenshot_rect.bottom() + delta.y())
            self.drag_position = event.pos()
            self.update()
            self._update_toolbar_position()
        else:
            pos = event.pos()
            margin = 10
            rect = self.screenshot_rect

            if pos.x() >= rect.right() - margin and pos.y() >= rect.bottom() - margin:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif rect.contains(pos):
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def _on_drag_end(self):
        pass

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragged = self.dragging or self.resizing
            self.dragging = False
            self.resizing = False
            if was_dragged:
                self._on_drag_end()

    def _update_toolbar_position(self):
        if self.toolbar:
            toolbar_width = self.toolbar.width()
            toolbar_x = self.screenshot_rect.right() - toolbar_width - 20
            toolbar_y = self.screenshot_rect.bottom() + 5
            self.toolbar.move(toolbar_x, toolbar_y)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            if self.toolbar:
                self.toolbar.close()

    def closeEvent(self, event):
        self._on_close()
        if self.toolbar:
            self.toolbar.close()
        super().closeEvent(event)

    def clear(self):
        self.text_items = []
        self.hide()
        if self.toolbar:
            self.toolbar.close()


class MaskTranslationOverlay(_BaseMaskOverlay):
    retry_signal = pyqtSignal()
    rect_changed = pyqtSignal(QRect)

    def __init__(self, sticky_manager=None):
        super().__init__(sticky_manager)
        self.all_original_text = ""
        self.all_translated_text = ""
        self.last_rect = QRect()

    def _set_text_items(self, items, screenshot_rect):
        self.text_items = items
        self.screenshot_rect = screenshot_rect
        self.last_rect = QRect(screenshot_rect)
        self.all_original_text = "\n".join([item[1] for item in items])
        self.all_translated_text = "\n".join([item[2] for item in items])

    def _toolbar_buttons(self):
        return [
            ("复制原文", "_copy_original", False),
            ("原文到便利贴", "_create_sticky_original", True),
            ("译文到便利贴", "_create_sticky_translated", False),
        ]

    def _paint_border_color(self) -> QColor:
        return QColor(255, 0, 0)

    def _paint_text_bg_color(self) -> QColor:
        return QColor(255, 255, 255, 255)

    def _paint_display_text(self) -> str:
        return self.all_translated_text

    def _copy_original(self):
        QApplication.clipboard().setText(self.all_original_text)

    def _copy_translated(self):
        QApplication.clipboard().setText(self.all_translated_text)

    def _create_sticky_original(self):
        if self.sticky_manager:
            sticky = self.sticky_manager.create_sticky_note()
            if sticky:
                sticky.set_content(self.all_original_text)
                sticky.move(self.screenshot_rect.topLeft())

    def _create_sticky_translated(self):
        if self.sticky_manager:
            sticky = self.sticky_manager.create_sticky_note()
            if sticky:
                sticky.set_content(self.all_translated_text)
                sticky.move(self.screenshot_rect.topLeft())

    def _on_drag_end(self):
        if self.screenshot_rect != self.last_rect:
            self.rect_changed.emit(QRect(self.screenshot_rect))
            self.last_rect = QRect(self.screenshot_rect)

    def update_translation(self, items):
        self.text_items = items
        self.all_original_text = "\n".join([item[1] for item in items])
        self.all_translated_text = "\n".join([item[2] for item in items])
        self.update()

    def _retry_translation(self):
        self.retry_signal.emit()

    def _take_screenshot(self):
        self.screenshot_signal.emit()

    def clear(self):
        self.all_original_text = ""
        self.all_translated_text = ""
        super().clear()


class MaskExtractOverlay(_BaseMaskOverlay):
    def __init__(self, sticky_manager=None):
        super().__init__(sticky_manager)
        self.all_text = ""

    def _set_text_items(self, items, screenshot_rect):
        self.text_items = items
        self.screenshot_rect = screenshot_rect
        self.all_text = "\n".join([item[1] for item in items])

    def _toolbar_buttons(self):
        return [
            ("复制文字", "_copy_text", False),
            ("文字到便利贴", "_create_sticky", True),
        ]

    def _paint_border_color(self) -> QColor:
        return QColor(255, 165, 0)

    def _paint_text_bg_color(self) -> QColor:
        return QColor(255, 255, 200, 255)

    def _paint_display_text(self) -> str:
        return self.all_text

    def _copy_text(self):
        QApplication.clipboard().setText(self.all_text)

    def _create_sticky(self):
        if self.sticky_manager:
            sticky = self.sticky_manager.create_sticky_note()
            if sticky:
                sticky.set_content(self.all_text)
                sticky.move(self.screenshot_rect.topLeft())

    def clear(self):
        self.all_text = ""
        super().clear()
