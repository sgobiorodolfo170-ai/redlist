import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from src.utils.logger import get_logger

logger = get_logger("RecordingIndicator")


class RecordingIndicator(QWidget):
    def __init__(self, recorder_thread, parent=None):
        super().__init__(parent)
        self.recorder_thread = recorder_thread
        self.start_time = time.time()
        self._setup_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_display)
        self._timer.start(1000)

        recorder_thread.recording_finished.connect(self._on_finished)
        recorder_thread.recording_error.connect(self._on_finished)

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 8px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.record_label = QLabel("🔴 录制中")
        layout.addWidget(self.record_label)

        self.time_label = QLabel("00:00")
        layout.addWidget(self.time_label)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(self.stop_btn)

        self.adjustSize()

        self._position_at_bottom_right()

    def _position_at_bottom_right(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 20
            y = geo.bottom() - self.height() - 20
            self.move(x, y)

    def _update_display(self):
        elapsed = int(time.time() - self.start_time)
        self.time_label.setText(f"{elapsed // 60:02d}:{elapsed % 60:02d}")

    def _on_stop(self):
        self.stop_btn.setEnabled(False)
        self.record_label.setText("⏹ 正在停止...")
        self.recorder_thread.stop()

    def _on_finished(self, *args):
        self._timer.stop()
        self.close()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
