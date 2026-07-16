import datetime
import os

from PyQt6.QtCore import QEventLoop, Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.recorder import RecordingIndicator, ScreenRecorderThread
from src.screenshot.region_selector import RegionSelector
from src.theme import COLORS
from src.utils.logger import get_logger

logger = get_logger("ScreenshotTab")


class ScreenshotTabPanel(QWidget):
    def __init__(self, settings, screenshot_manager, main_window, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.screenshot_manager = screenshot_manager
        self.main_window = main_window
        self.recorder_thread = None
        self.recording_indicator = None
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: white;
            }}
            QLabel {{
                color: {COLORS["text_primary"]};
            }}
            QToolTip {{
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                padding: 12px 16px;
                color: {COLORS["text_primary"]};
                font-size: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(16)

        self.screenshot_btn = QPushButton("📷  截图")
        self.screenshot_btn.setFixedHeight(52)
        self.screenshot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.screenshot_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["primary"]};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
            QPushButton:pressed {{
                background-color: #A93226;
            }}
        """)
        self.screenshot_btn.clicked.connect(self._start_screenshot)

        self.recording_btn = QPushButton("🎥  录屏")
        self.recording_btn.setFixedHeight(52)
        self.recording_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.recording_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2980B9;
            }}
            QPushButton:pressed {{
                background-color: #2471A3;
            }}
        """)
        self.recording_btn.clicked.connect(self._start_recording)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addWidget(self.screenshot_btn, 1)
        btn_row.addWidget(self.recording_btn, 1)
        layout.addLayout(btn_row)

        desc_label = QLabel("截图直接保存到截图路径，录屏保存到录屏路径")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']}; padding: 4px 0;")
        layout.addWidget(desc_label)

        layout.addStretch()

    def _start_screenshot(self):
        logger.debug("Starting screenshot from tab")
        self.screenshot_manager.start_region_screenshot()

    def _start_recording(self):
        has_cv2 = True
        try:
            import cv2  # noqa: F401
        except ImportError:
            has_cv2 = False

        if not has_cv2:
            QMessageBox.warning(self, "提示", "缺少 OpenCV 库 (cv2)，无法录屏")
            return

        self.main_window.hide()
        QTimer.singleShot(300, self._do_region_select)

    def _do_region_select(self):
        selector = RegionSelector()
        selector.setup_fullscreen()

        loop = QEventLoop()
        selector.closed.connect(loop.quit)
        loop.exec()

        rect = selector.selected_rect
        if rect is None or rect.width() < 50 or rect.height() < 50:
            self.main_window.show()
            return

        self._confirm_recording(selector.selected_rect)

    def _confirm_recording(self, rect):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        dialog = QWidget(None, flags)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        dialog.setStyleSheet("""
            QWidget {
                background-color: rgba(44, 62, 80, 220);
                border-radius: 12px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
                font-weight: bold;
            }
        """)

        layout = QHBoxLayout(dialog)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)

        info_label = QLabel(f"🎥 选区: {rect.width()}×{rect.height()}")
        layout.addWidget(info_label)

        confirm_btn = QPushButton("▶ 开始录制")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        layout.addWidget(confirm_btn)

        cancel_btn = QPushButton("✕ 取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        layout.addWidget(cancel_btn)

        dialog.adjustSize()
        screen_geo = self.screen().availableGeometry() if self.screen() else None
        if screen_geo:
            x = rect.right() - dialog.width() - 10
            y = rect.bottom() + 10
            if y + dialog.height() > screen_geo.bottom():
                y = rect.top() - dialog.height() - 10
            if x < screen_geo.left():
                x = screen_geo.left() + 10
            dialog.move(x, y)

        result = [False]

        def on_confirm():
            result[0] = True
            dialog.close()
            loop.quit()

        def on_cancel():
            result[0] = False
            dialog.close()
            loop.quit()

        confirm_btn.clicked.connect(on_confirm)
        cancel_btn.clicked.connect(on_cancel)

        dialog.show()

        loop = QEventLoop()
        loop.exec()

        if result[0]:
            self._start_recording_thread(rect)
        else:
            self.main_window.show()

    def _start_recording_thread(self, rect):
        output_dir = self.settings.get_recording_path()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"rec_{timestamp}.mp4")

        self.recorder_thread = ScreenRecorderThread(rect, output_path, parent=self)
        self.recorder_thread.recording_finished.connect(self._on_recording_finished)
        self.recorder_thread.recording_error.connect(self._on_recording_error)

        self.recording_indicator = RecordingIndicator(self.recorder_thread)
        self.recording_indicator.show()

        self.recorder_thread.start()

    def _on_recording_finished(self, path):
        self.recording_indicator = None
        self.recorder_thread = None
        self.main_window.show()
        QMessageBox.information(self, "录屏完成", f"录制已保存到:\n{path}")

    def _on_recording_error(self, msg):
        self.recording_indicator = None
        self.recorder_thread = None
        self.main_window.show()
        QMessageBox.critical(self, "录屏出错", msg)
