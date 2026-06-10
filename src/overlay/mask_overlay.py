from typing import List, Tuple

from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QWidget


class MaskTranslationOverlay(QWidget):
    retry_signal = pyqtSignal()
    screenshot_signal = pyqtSignal()
    rect_changed = pyqtSignal(QRect)

    def __init__(self, sticky_manager=None):
        super().__init__()
        self.text_items: List[Tuple[QRect, str, str]] = []
        self.sticky_manager = sticky_manager
        self.toolbar = None
        self.screenshot_rect = QRect()
        self.all_original_text = ""
        self.all_translated_text = ""
        self.font_size = 12
        self.dragging = False
        self.resizing = False
        self.drag_position = QPoint()
        self.last_rect = QRect()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_texts(self, items: List[Tuple[QRect, str, str]], screenshot_rect: QRect):
        self.text_items = items
        self.screenshot_rect = screenshot_rect
        self.last_rect = QRect(screenshot_rect)

        self.all_original_text = "\n".join([item[1] for item in items])
        self.all_translated_text = "\n".join([item[2] for item in items])

        if items and items[0][0].height() > 0:
            estimated_font_size = max(10, min(items[0][0].height() // 2, 18))
            self.font_size = estimated_font_size + 1
        else:
            self.font_size = 13

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

    def _create_toolbar(self):
        if self.toolbar:
            self.toolbar.close()

        self.toolbar = QWidget()
        self.toolbar.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
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

        copy_original_btn = QPushButton("复制原文")
        copy_original_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_original_btn.setStyleSheet("""
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
        copy_original_btn.clicked.connect(self._copy_original)
        layout.addWidget(copy_original_btn)

        sticky_original_btn = QPushButton("原文到便利贴")
        sticky_original_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sticky_original_btn.setStyleSheet("""
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
        sticky_original_btn.clicked.connect(self._create_sticky_original)
        layout.addWidget(sticky_original_btn)

        sticky_trans_btn = QPushButton("译文到便利贴")
        sticky_trans_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sticky_trans_btn.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056B3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        sticky_trans_btn.clicked.connect(self._create_sticky_translated)
        layout.addWidget(sticky_trans_btn)

        toolbar_width = layout.sizeHint().width()
        self.toolbar.setFixedWidth(toolbar_width + 20)

        toolbar_x = self.screenshot_rect.right() - toolbar_width - 20
        toolbar_y = self.screenshot_rect.bottom() + 5
        self.toolbar.move(toolbar_x, toolbar_y)
        self.toolbar.show()

    def _copy_original(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.all_original_text)

    def _copy_translated(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.all_translated_text)

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

    def _take_screenshot(self):
        """触发截图保存信号"""
        self.screenshot_signal.emit()

    def _retry_translation(self):
        """触发重新翻译信号"""
        self.retry_signal.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QBrush(QColor(0, 0, 0, 120)))

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.screenshot_rect, QBrush(QColor(0, 0, 0, 0)))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawRect(self.screenshot_rect.adjusted(0, 0, -1, -1))

        text_box_rect = self.screenshot_rect.adjusted(1, 1, -1, -1)

        painter.fillRect(text_box_rect, QBrush(QColor(255, 255, 255, 255)))

        text_rect = text_box_rect.adjusted(10, 10, -10, -10)

        if text_rect.width() > 0 and text_rect.height() > 0:
            font_size = self._calculate_font_size(text_rect, self.all_translated_text)

            painter.setPen(QColor(50, 50, 50))
            font = QFont("Microsoft YaHei", font_size)
            painter.setFont(font)

            painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, self.all_translated_text)

    def _calculate_font_size(self, rect, text):
        if not text:
            return 12

        min_size = 8
        max_size = 24
        text_length = len(text)

        area = rect.width() * rect.height()

        if text_length == 0:
            return 12

        estimated_size = int((area / text_length) ** 0.5 / 2)
        estimated_size = max(min_size, min(max_size, estimated_size))

        return estimated_size

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

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragged = self.dragging or self.resizing
            self.dragging = False
            self.resizing = False

            if was_dragged and (self.screenshot_rect != self.last_rect):
                self.rect_changed.emit(QRect(self.screenshot_rect))
                self.last_rect = QRect(self.screenshot_rect)

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
        if self.toolbar:
            self.toolbar.close()
        super().closeEvent(event)

    def update_translation(self, items: List[Tuple[QRect, str, str]]):
        self.text_items = items
        self.all_original_text = "\n".join([item[1] for item in items])
        self.all_translated_text = "\n".join([item[2] for item in items])
        self.update()

    def clear(self):
        self.text_items = []
        self.all_original_text = ""
        self.all_translated_text = ""
        self.hide()
        if self.toolbar:
            self.toolbar.close()


class MaskExtractOverlay(QWidget):
    screenshot_signal = pyqtSignal()

    def __init__(self, sticky_manager=None):
        super().__init__()
        self.text_items: List[Tuple[QRect, str]] = []
        self.sticky_manager = sticky_manager
        self.toolbar = None
        self.screenshot_rect = QRect()
        self.all_text = ""
        self.font_size = 12
        self.dragging = False
        self.resizing = False
        self.drag_position = QPoint()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_texts(self, items: List[Tuple[QRect, str]], screenshot_rect: QRect):
        self.text_items = items
        self.screenshot_rect = screenshot_rect

        self.all_text = "\n".join([item[1] for item in items])

        if items and items[0][0].height() > 0:
            estimated_font_size = max(10, min(items[0][0].height() // 2, 18))
            self.font_size = estimated_font_size + 1
        else:
            self.font_size = 13

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

    def _create_toolbar(self):
        if self.toolbar:
            self.toolbar.close()

        self.toolbar = QWidget()
        self.toolbar.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
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

        copy_btn = QPushButton("复制文字")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("""
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
        copy_btn.clicked.connect(self._copy_text)
        layout.addWidget(copy_btn)

        sticky_btn = QPushButton("文字到便利贴")
        sticky_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sticky_btn.setStyleSheet("""
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
        sticky_btn.clicked.connect(self._create_sticky)
        layout.addWidget(sticky_btn)

        toolbar_width = layout.sizeHint().width()
        self.toolbar.setFixedWidth(toolbar_width + 20)

        toolbar_x = self.screenshot_rect.right() - toolbar_width - 20
        toolbar_y = self.screenshot_rect.bottom() + 5
        self.toolbar.move(toolbar_x, toolbar_y)
        self.toolbar.show()

    def _copy_text(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.all_text)

    def _create_sticky(self):
        if self.sticky_manager:
            sticky = self.sticky_manager.create_sticky_note()
            if sticky:
                sticky.set_content(self.all_text)
                sticky.move(self.screenshot_rect.topLeft())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QBrush(QColor(0, 0, 0, 120)))

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.screenshot_rect, QBrush(QColor(0, 0, 0, 0)))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        pen = QPen(QColor(255, 165, 0), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawRect(self.screenshot_rect.adjusted(0, 0, -1, -1))

        text_box_rect = self.screenshot_rect.adjusted(1, 1, -1, -1)

        painter.fillRect(text_box_rect, QBrush(QColor(255, 255, 200, 255)))

        text_rect = text_box_rect.adjusted(10, 10, -10, -10)

        if text_rect.width() > 0 and text_rect.height() > 0:
            font_size = self._calculate_font_size(text_rect, self.all_text)

            painter.setPen(QColor(50, 50, 50))
            font = QFont("Microsoft YaHei", font_size)
            painter.setFont(font)

            painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, self.all_text)

    def _calculate_font_size(self, rect, text):
        if not text:
            return 12

        min_size = 8
        max_size = 24
        text_length = len(text)

        area = rect.width() * rect.height()

        if text_length == 0:
            return 12

        estimated_size = int((area / text_length) ** 0.5 / 2)
        estimated_size = max(min_size, min(max_size, estimated_size))

        return estimated_size

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

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False

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
        if self.toolbar:
            self.toolbar.close()
        super().closeEvent(event)

    def clear(self):
        self.text_items = []
        self.all_text = ""
        self.hide()
        if self.toolbar:
            self.toolbar.close()
