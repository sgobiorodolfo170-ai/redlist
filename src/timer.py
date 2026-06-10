import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget

from src.theme import COLORS
from src.utils.logger import get_logger
from src.utils.sound import play_sound

logger = get_logger("Timer")


class TimerPanel(QWidget):

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.is_running = False
        self.is_pomodoro = False
        self.remaining_seconds = 0
        self.total_seconds = 0
        self.pomodoro_work = 25 * 60
        self.pomodoro_break = 5 * 60
        self.minutes_value = 25

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)

        header = QLabel("定时器")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS['text_primary']};
            padding: 8px 0;
        """)
        layout.addWidget(header)

        mode_layout = QHBoxLayout()
        self.countdown_btn = QPushButton("倒计时")
        self.countdown_btn.setCheckable(True)
        self.countdown_btn.setChecked(True)
        self.countdown_btn.setFixedHeight(32)
        self.countdown_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
            }}
            QPushButton:!checked {{
                background-color: white;
                color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
            }}
        """)
        self.countdown_btn.clicked.connect(lambda: self.set_mode('countdown'))
        mode_layout.addWidget(self.countdown_btn)

        self.pomodoro_btn = QPushButton("番茄钟")
        self.pomodoro_btn.setCheckable(True)
        self.pomodoro_btn.setFixedHeight(32)
        self.pomodoro_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
            }}
        """)
        self.pomodoro_btn.clicked.connect(lambda: self.set_mode('pomodoro'))
        mode_layout.addWidget(self.pomodoro_btn)
        layout.addLayout(mode_layout)

        self.input_frame = QFrame()
        input_layout = QHBoxLayout(self.input_frame)
        input_layout.setContentsMargins(0, 12, 0, 12)
        input_layout.setSpacing(8)

        input_label = QLabel("设置分钟:")
        input_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        input_layout.addWidget(input_label)

        self.minutes_display = QLabel("25")
        self.minutes_display.setFixedWidth(50)
        self.minutes_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.minutes_display.setStyleSheet(f"""
            QLabel {{
                background-color: white;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
                color: {COLORS['text_primary']};
                padding: 4px;
            }}
        """)
        input_layout.addWidget(self.minutes_display)

        btn_style = f"""
            QPushButton {{
                background-color: {COLORS['background']};
                color: {COLORS['text_primary']};
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
            }}
            QPushButton:hover {{
                background-color: #D5DBDB;
                border-color: {COLORS['primary']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: white;
            }}
        """

        self.decrease_btn = QPushButton("-")
        self.decrease_btn.setStyleSheet(btn_style)
        self.decrease_btn.clicked.connect(self.decrease_minutes)
        input_layout.addWidget(self.decrease_btn)

        self.increase_btn = QPushButton("+")
        self.increase_btn.setStyleSheet(btn_style)
        self.increase_btn.clicked.connect(self.increase_minutes)
        input_layout.addWidget(self.increase_btn)

        input_layout.addStretch()
        layout.addWidget(self.input_frame)

        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(60)
        font.setBold(True)
        self.time_label.setFont(font)
        self.time_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            padding: 16px 0;
        """)
        layout.addWidget(self.time_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background-color: {COLORS['background']};
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress)

        layout.addStretch()

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 16, 0, 0)

        self.start_btn = QPushButton("开始")
        self.start_btn.setFixedHeight(40)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
        """)
        self.start_btn.clicked.connect(self.toggle_timer)
        control_layout.addWidget(self.start_btn)

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setFixedHeight(40)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #E74C3C;
                border: 2px solid #E74C3C;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ECF0F1;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_timer)
        control_layout.addWidget(self.reset_btn)

        layout.addLayout(control_layout)
        self.reset_timer()

    def increase_minutes(self):
        if self.minutes_value < 180:
            self.minutes_value += 1
            self.minutes_display.setText(str(self.minutes_value))
            if not self.is_running:
                self.reset_timer()

    def decrease_minutes(self):
        if self.minutes_value > 1:
            self.minutes_value -= 1
            self.minutes_display.setText(str(self.minutes_value))
            if not self.is_running:
                self.reset_timer()

    def set_mode(self, mode):
        if mode == 'countdown':
            self.countdown_btn.setChecked(True)
            self.pomodoro_btn.setChecked(False)
            self.input_frame.setVisible(True)
            self.is_pomodoro = False
            self.reset_timer()
        else:
            self.countdown_btn.setChecked(False)
            self.pomodoro_btn.setChecked(True)
            self.input_frame.setVisible(False)
            self.is_pomodoro = True
            self.reset_timer()

    def toggle_timer(self):
        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        if not self.is_running:
            if self.is_pomodoro:
                if self.remaining_seconds == 0:
                    self.remaining_seconds = self.pomodoro_work
                    self.total_seconds = self.pomodoro_work
            else:
                if self.remaining_seconds == 0:
                    self.total_seconds = self.minutes_value * 60
                    self.remaining_seconds = self.total_seconds

            self.is_running = True
            self.timer.start(1000)
            self.start_btn.setText("暂停")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F39C12;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #E67E22;
                }
            """)
            self.increase_btn.setEnabled(False)
            self.decrease_btn.setEnabled(False)

    def pause_timer(self):
        self.is_running = False
        self.timer.stop()
        self.start_btn.setText("继续")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)

    def reset_timer(self):
        self.timer.stop()
        self.is_running = False

        if self.is_pomodoro:
            self.total_seconds = self.pomodoro_work
            self.remaining_seconds = self.pomodoro_work
        else:
            self.total_seconds = self.minutes_value * 60
            self.remaining_seconds = self.total_seconds

        self.update_display()
        self.start_btn.setText("开始")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
        self.increase_btn.setEnabled(True)
        self.decrease_btn.setEnabled(True)

    def tick(self):
        self.remaining_seconds -= 1
        self.update_display()

        if self.remaining_seconds <= 0:
            self.timer.stop()
            self.is_running = False
            self.on_timer_finished()

    def update_display(self):
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.time_label.setText(f"{minutes:02d}:{seconds:02d}")

        if self.total_seconds > 0:
            progress = int((self.remaining_seconds / self.total_seconds) * 100)
            self.progress.setValue(progress)

    def on_timer_finished(self):
        if self.is_pomodoro:
            if self.total_seconds == self.pomodoro_work:
                self.show_finish_dialog("工作时间结束！", "开始休息")
                self.remaining_seconds = self.pomodoro_break
                self.total_seconds = self.pomodoro_break
            else:
                self.show_finish_dialog("休息结束！", "开始工作")
                self.remaining_seconds = self.pomodoro_work
                self.total_seconds = self.pomodoro_work
        else:
            self.show_finish_dialog("时间到！", "确定")

        if self.settings.get('play_sound', True):
            try:
                sound_path = self.settings.get_alarm_sound_path()
                if os.path.exists(sound_path):
                    play_sound(sound_path)
                else:
                    import winsound
                    winsound.MessageBeep(winsound.MB_OK)
            except OSError as e:
                logger.error(f"Failed to play sound: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error playing sound: {e}")

    def show_finish_dialog(self, title, btn_text):
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(title)
        msg.addButton(btn_text, QMessageBox.ButtonRole.AcceptRole)
        msg.exec()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
