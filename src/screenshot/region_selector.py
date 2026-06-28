from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class RegionSelector(QWidget):
    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.start_point = QPoint()
        self.end_point = QPoint()
        self.is_selecting = False
        self.selected_rect = None
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def setup_fullscreen(self):
        screens = QGuiApplication.screens()
        if screens:
            total_geometry = screens[0].geometry()
            for screen in screens[1:]:
                total_geometry = total_geometry.united(screen.geometry())
            self.setGeometry(total_geometry)
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QBrush(QColor(0, 0, 0, 100)))

        if self.is_selecting:
            select_rect = QRect(self.start_point, self.end_point).normalized()
            painter.setPen(QPen(QColor(255, 0, 0), 2, Qt.PenStyle.DashLine))
            painter.drawRect(select_rect)

            painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
            painter.drawRect(select_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.pos()
            self.end_point = event.pos()
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            self.selected_rect = QRect(self.start_point, self.end_point).normalized()
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.selected_rect = None
            self.close()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
