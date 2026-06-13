import datetime
import os
from pathlib import Path

from PyQt6.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.utils.logger import get_logger

logger = get_logger("Screenshot")


class ConfirmDialog(QDialog):
    def __init__(self, cancel_callback, parent=None):
        super().__init__(parent)
        self.cancel_callback = cancel_callback
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_callback()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.cancel_callback()
        else:
            super().mousePressEvent(event)


class ScreenshotManager:
    def __init__(self, settings):
        self.settings = settings
        self.overlay = None
        self.confirm_dialog = None
        self.current_pixmap = None
        self.main_window = None

    def get_panel(self):
        return ScreenshotPanel(self.settings, self)

    def get_favorites_path(self):
        """获取截图保存路径（使用设置中的路径）"""
        # 使用设置中的截图保存路径
        fav_path = self.settings.get_screenshot_path()
        Path(fav_path).mkdir(parents=True, exist_ok=True)
        return fav_path

    def start_region_screenshot(self):
        """开始区域截图"""
        logger.debug("Starting region screenshot...")
        # 隐藏主窗口
        if self.main_window and hasattr(self.main_window, 'isVisible'):
            try:
                if self.main_window.isVisible():
                    self.main_window.hide()
                    logger.debug("Main window hidden")
            except RuntimeError:
                pass

        QTimer.singleShot(300, self._do_region_screenshot)

    def _do_region_screenshot(self):
        logger.debug("Creating overlay...")
        self.overlay = ScreenshotOverlay('region')
        self.overlay.screenshot_taken.connect(self.on_screenshot_taken)
        self.overlay.cancelled.connect(self.on_screenshot_cancelled)
        self.overlay.showFullScreen()
        self.overlay.activateWindow()
        self.overlay.raise_()
        logger.debug("Overlay shown, visible: %s", self.overlay.isVisible())

    def on_screenshot_cancelled(self):
        """截图取消"""
        logger.debug("Cancelled")
        try:
            if self.confirm_dialog:
                self.confirm_dialog.close()
                self.confirm_dialog = None
        except RuntimeError:
            pass

        try:
            if self.overlay:
                self.overlay = None
        except RuntimeError:
            pass

        try:
            if self.main_window and hasattr(self.main_window, 'isVisible'):
                if not self.main_window.isVisible():
                    self.main_window.show()
        except RuntimeError:
            pass

    def on_screenshot_taken(self, pixmap, rect):
        """截图完成，显示确认对话框"""
        logger.debug("Taken, size = %sx%s, rect = %s", pixmap.width(), pixmap.height(), rect)
        self.current_pixmap = pixmap
        self.current_rect = rect

        self.show_confirm_dialog(pixmap, rect)

    def show_confirm_dialog(self, pixmap, rect=None):
        """显示确认对话框（靠近选区右下角）"""
        screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else None

        self.confirm_dialog = ConfirmDialog(lambda: self.on_confirm_cancel(False), None)
        self.confirm_dialog.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
        )
        self.confirm_dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.confirm_dialog.setAutoFillBackground(False)

        dialog_width = 40
        dialog_height = 40

        if rect:
            x = rect.right() - dialog_width - 10
            y = rect.bottom() + 10

            if y + dialog_height > screen_geo.bottom():
                y = rect.top() - dialog_height - 10
            if x < screen_geo.left():
                x = screen_geo.left() + 10
        else:
            x = screen_geo.right() - dialog_width - 20 if screen_geo else 100
            y = screen_geo.bottom() - dialog_height - 20 if screen_geo else 100

        self.confirm_dialog.setGeometry(x, y, dialog_width, dialog_height)

        self.confirm_dialog.setStyleSheet("""
            QDialog {
                background-color: transparent;
            }
        """)

        layout = QHBoxLayout(self.confirm_dialog)
        layout.setContentsMargins(0, 0, 0, 0)

        confirm_btn = QPushButton("✓")
        confirm_btn.setFixedSize(40, 40)
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #27AE60;
                border: none;
                border-radius: 20px;
                font-size: 36px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(39, 174, 96, 30);
                color: #229954;
            }
            QPushButton:pressed {
                color: #1E8449;
            }
        """)
        confirm_btn.clicked.connect(lambda: self.on_confirm_cancel(True))
        layout.addWidget(confirm_btn)

        self.confirm_dialog.show()
        self.confirm_dialog.raise_()
        self.confirm_dialog.activateWindow()

    def on_confirm_cancel(self, confirmed):
        """处理确认/取消"""
        logger.debug("Confirm = %s", confirmed)
        try:
            if self.confirm_dialog:
                self.confirm_dialog.close()
                self.confirm_dialog = None
        except RuntimeError:
            pass

        try:
            if self.overlay:
                self.overlay.close()
                self.overlay = None
        except RuntimeError:
            pass

        if confirmed and self.current_pixmap:
            logger.debug("Saving to favorites...")
            self.save_to_favorites(self.current_pixmap)

        self.current_pixmap = None

        try:
            if self.main_window and hasattr(self.main_window, 'isVisible'):
                if not self.main_window.isVisible():
                    self.main_window.show()
        except RuntimeError:
            pass

    def save_to_favorites(self, pixmap):
        """保存到收藏夹"""
        fav_path = self.get_favorites_path()

        # 确保目录存在
        import pathlib
        pathlib.Path(fav_path).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fav_{timestamp}.png"
        filepath = os.path.join(fav_path, filename)

        # 保存截图
        success = pixmap.save(filepath, "PNG")
        logger.debug("Save result = %s, path = %s", success, filepath)

        # 复制到剪贴板
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(pixmap)

        return success


class ScreenshotPanel(QWidget):
    """截图面板（已不再使用，保留以防需要）"""
    def __init__(self, settings, manager):
        super().__init__()
        self.settings = settings
        self.manager = manager
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("截图工具（点击工具栏图标使用）"))


class ScreenshotOverlay(QWidget):
    screenshot_taken = pyqtSignal(object, object)  # (pixmap, rect)
    cancelled = pyqtSignal()

    def __init__(self, mode='region'):
        super().__init__()
        self.mode = mode
        self.selection_start = None
        self.selection_end = None
        self.capturing = False
        self.selected_rect = None
        self.dragging = False
        self.resizing = False
        self.drag_position = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)

        self.setGeometry(QGuiApplication.primaryScreen().geometry())
        self.showFullScreen()
        self.activateWindow()
        self.raise_()
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)

        # 先填充全屏蒙版
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.selected_rect:
            # 清除截图区域的蒙版（绘制透明）
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.selected_rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # 绘制截图区域边框
            pen = QPen(QColor(231, 76, 60), 1)
            painter.setPen(pen)
            painter.drawRect(self.selected_rect)

            # 显示尺寸
            w = self.selected_rect.width()
            h = self.selected_rect.height()
            text = f"{w} x {h}"
            painter.setPen(QColor(231, 76, 60))
            painter.drawText(self.selected_rect.x() + 5, self.selected_rect.y() + 20, text)
        elif self.selection_start and self.selection_end:
            rect = QRect(self.selection_start, self.selection_end).normalized()

            # 清除截图区域的蒙版（绘制透明）
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            # 绘制截图区域边框
            pen = QPen(QColor(231, 76, 60), 1)
            painter.setPen(pen)
            painter.drawRect(rect)

            # 显示尺寸
            w = rect.width()
            h = rect.height()
            text = f"{w} x {h}"
            painter.setPen(QColor(231, 76, 60))
            painter.drawText(rect.x() + 5, rect.y() + 20, text)

    def closeEvent(self, event):
        self.cancelled.emit()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.close()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()

            if self.selected_rect:
                margin = 10

                if pos.x() >= self.selected_rect.right() - margin and pos.y() >= self.selected_rect.bottom() - margin:
                    self.resizing = True
                    self.drag_position = pos
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif self.selected_rect.contains(pos):
                    self.dragging = True
                    self.drag_position = pos
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    self.selection_start = pos
                    self.selection_end = pos
                    self.capturing = True
                    self.selected_rect = None
                    self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.selection_start = pos
                self.selection_end = pos
                self.capturing = True

            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging and self.selected_rect:
            delta = event.pos() - self.drag_position
            self.selected_rect.translate(delta)
            self.drag_position = event.pos()
            self.update()
        elif self.resizing and self.selected_rect:
            delta = event.pos() - self.drag_position
            self.selected_rect.setRight(self.selected_rect.right() + delta.x())
            self.selected_rect.setBottom(self.selected_rect.bottom() + delta.y())
            self.drag_position = event.pos()
            self.update()
        elif self.capturing:
            self.selection_end = event.pos()
            self.update()
        else:
            if self.selected_rect:
                pos = event.pos()
                margin = 10

                if pos.x() >= self.selected_rect.right() - margin and pos.y() >= self.selected_rect.bottom() - margin:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif self.selected_rect.contains(pos):
                    self.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    self.setCursor(Qt.CursorShape.CrossCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging or self.resizing:
                self.dragging = False
                self.resizing = False
                if self.selected_rect and self.selected_rect.width() > 10 and self.selected_rect.height() > 10:
                    self.capture_screen(self.selected_rect)
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self.capturing:
                self.capturing = False
                if self.selection_start and self.selection_end:
                    rect = QRect(self.selection_start, self.selection_end).normalized()
                    if rect.width() > 10 and rect.height() > 10:
                        self.selected_rect = rect
                        self.capture_screen(rect)

            self.update()

    def capture_screen(self, rect):
        screen = QGuiApplication.primaryScreen()
        if screen:
            pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
            self.screenshot_taken.emit(pixmap, rect)
