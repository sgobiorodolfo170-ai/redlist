from typing import List, Tuple

from PyQt6.QtCore import QRect, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class TranslationOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.text_items: List[Tuple[QRect, str, str]] = []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def set_texts(self, items: List[Tuple[QRect, str, str]]):
        self.text_items = items
        if items:
            total_rect = items[0][0]
            for rect, _, _ in items[1:]:
                total_rect = total_rect.united(rect)
            self.setGeometry(total_rect)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for rect, original, translated in self.text_items:
            rel_rect = QRect(
                rect.x() - self.x(),
                rect.y() - self.y(),
                rect.width(),
                rect.height()
            )

            painter.fillRect(rel_rect, QBrush(QColor(255, 255, 255, 220)))

            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawRect(rel_rect)

            painter.setPen(QColor(0, 0, 0))
            font_size = max(10, min(rect.height() // 3, 16))
            font = QFont("Microsoft YaHei", font_size)
            painter.setFont(font)

            text_rect = rel_rect.adjusted(4, 2, -4, -2)
            painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, translated)

    def show_for_duration(self, duration_ms: int = 15000):
        self.show()
        QTimer.singleShot(duration_ms, self.hide)

    def clear(self):
        self.text_items = []
        self.hide()


class TextExtractOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.text_items: List[Tuple[QRect, str]] = []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def set_texts(self, items: List[Tuple[QRect, str]]):
        self.text_items = items
        if items:
            total_rect = items[0][0]
            for rect, _ in items[1:]:
                total_rect = total_rect.united(rect)
            self.setGeometry(total_rect)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for rect, text in self.text_items:
            rel_rect = QRect(
                rect.x() - self.x(),
                rect.y() - self.y(),
                rect.width(),
                rect.height()
            )

            painter.fillRect(rel_rect, QBrush(QColor(255, 255, 200, 220)))

            painter.setPen(QPen(QColor(200, 180, 100), 1))
            painter.drawRect(rel_rect)

            painter.setPen(QColor(0, 0, 0))
            font_size = max(10, min(rect.height() // 3, 16))
            font = QFont("Microsoft YaHei", font_size)
            painter.setFont(font)

            text_rect = rel_rect.adjusted(4, 2, -4, -2)
            painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, text)

    def show_for_duration(self, duration_ms: int = 15000):
        self.show()
        QTimer.singleShot(duration_ms, self.hide)

    def clear(self):
        self.text_items = []
        self.hide()
