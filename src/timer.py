import math
import os
import random
import sys
import time as _time
import threading as _th

from PyQt6.QtCore import QTimer, QTime, QUrl, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QSpinBox, QTimeEdit, QVBoxLayout, QWidget

from src.theme import COLORS
from src.utils.logger import get_logger
from src.utils.sound import play_sound

logger = get_logger("Timer")


class EcgWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(160)
        self.setMinimumWidth(300)
        self.setStyleSheet("background: white;")
        self._bpm = 72
        self._running = False
        self._phase = 0.0
        self._buffer = []
        self._elapsed = 0.0
        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.setInterval(33)
        self._pen_trace = QPen(QColor("#000000"), 1.5)
        self._pen_text = QPen(QColor("#000000"))
        self._font_bpm = QFont("Consolas", 10, QFont.Weight.Bold)
        self._path = QPainterPath()

    def set_bpm(self, bpm):
        self._bpm = max(30, min(200, bpm))

    def start(self):
        self._running = True
        self._anim_timer.start()

    def stop(self):
        self._running = False
        self._anim_timer.stop()

    def clear(self):
        self._buffer.clear()
        self._phase = 0
        self._elapsed = 0
        self.update()

    @staticmethod
    def _ecg_signal(phase):
        t = phase % 1.0
        p = 0.15 * math.exp(-((t - 0.15) ** 2) / (2 * 0.008 ** 2))
        q = -0.12 * math.exp(-((t - 0.30) ** 2) / (2 * 0.010 ** 2))
        r = 1.0 * math.exp(-((t - 0.35) ** 2) / (2 * 0.015 ** 2))
        s = -0.10 * math.exp(-((t - 0.42) ** 2) / (2 * 0.012 ** 2))
        tw = 0.30 * math.exp(-((t - 0.65) ** 2) / (2 * 0.045 ** 2))
        return p + q + r + s + tw

    def _tick(self):
        dt = 0.033
        self._phase += dt * self._bpm / 60
        self._elapsed += dt
        value = self._ecg_signal(self._phase)
        self._buffer.append(value)
        w = self.width()
        if len(self._buffer) > w:
            self._buffer[:len(self._buffer) - w] = []
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), Qt.GlobalColor.white)

        w = self.width()
        h = self.height()
        m = 6

        if not self._buffer:
            p.end()
            return

        buf = self._buffer
        pw = len(buf)
        mid = h / 2 + 50
        amp = (h - 2 * m) / 2.4

        self._path = QPainterPath()
        self._path.moveTo(0, mid - buf[0] * amp)
        for i in range(1, pw):
            x = i
            y = mid - buf[i] * amp
            self._path.lineTo(x, y)

        p.setPen(self._pen_trace)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(self._path)

        p.setPen(self._pen_text)
        p.setFont(self._font_bpm)
        p.drawText(w - 80, 14, f"{self._bpm} BPM")

        p.end()


class HeartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 240)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self._beating = False
        self._bpm = 72

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._view = QWebEngineView()
        self._view.setStyleSheet("background: transparent;")
        self._view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self._view.setUrl(QUrl.fromLocalFile(self._resource_path()))
        layout.addWidget(self._view)

    @staticmethod
    def _resource_path():
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "resources", "heartbeat3d", "index.html")

    def set_bpm(self, bpm):
        self._bpm = max(30, min(200, bpm))
        self._view.page().runJavaScript(f"setBPM({self._bpm})")

    def set_beating(self, on):
        self._beating = on
        js = "startHeart()" if on else "stopHeart()"
        self._view.page().runJavaScript(js)

    def is_beating(self):
        return self._beating

    def cleanup(self):
        self._view.page().runJavaScript("stopHeart()")
        self._view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self._view.setUrl(QUrl("about:blank"))
        self._view.deleteLater()


class TimerPanel(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.is_running = False
        self.is_alarm = False
        self.is_heartbeat = False
        self.remaining_seconds = 0
        self.total_seconds = 0
        self.minutes_value = 25
        self.alarm_time = QTime(8, 0)
        self.alarm_armed = False
        self._alarm_loop_active = False
        self.bpm_min = self.settings.get("bpm_min", 60)
        self.bpm_max = self.settings.get("bpm_max", 120)
        self.current_bpm = 72
        self._bpm_vary_timer = QTimer()
        self._bpm_vary_timer.timeout.connect(self._vary_bpm)

        self.init_ui()

    @staticmethod
    def _btn_style(bg, hover):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)

        header = QLabel("定时器")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS["text_primary"]};
            padding: 8px 0;
        """)
        layout.addWidget(header)

        mode_layout = QHBoxLayout()
        self.pomodoro_btn = self._make_mode_btn("番茄钟", checked=True)
        self.pomodoro_btn.clicked.connect(lambda: self.set_mode("pomodoro"))
        mode_layout.addWidget(self.pomodoro_btn)

        self.alarm_btn = self._make_mode_btn("闹铃")
        self.alarm_btn.clicked.connect(lambda: self.set_mode("alarm"))
        mode_layout.addWidget(self.alarm_btn)

        self.heartbeat_btn = self._make_mode_btn("心跳")
        self.heartbeat_btn.clicked.connect(lambda: self.set_mode("heartbeat"))
        mode_layout.addWidget(self.heartbeat_btn)

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
                color: {COLORS["text_primary"]};
                padding: 4px;
            }}
        """)
        input_layout.addWidget(self.minutes_display)

        btn_style = f"""
            QPushButton {{
                background-color: {COLORS["background"]};
                color: {COLORS["text_primary"]};
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
                border-color: {COLORS["primary"]};
            }}
            QPushButton:pressed {{
                background-color: {COLORS["primary"]};
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

        self.alarm_frame = QFrame()
        alarm_input_layout = QHBoxLayout(self.alarm_frame)
        alarm_input_layout.setContentsMargins(0, 12, 0, 12)
        alarm_input_layout.setSpacing(8)

        alarm_label = QLabel("闹铃时间:")
        alarm_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        alarm_input_layout.addWidget(alarm_label)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setTime(self.alarm_time)
        self.time_edit.setFixedWidth(120)
        self.time_edit.setStyleSheet(f"""
            QTimeEdit {{
                background-color: white;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
                color: {COLORS["text_primary"]};
                padding: 4px;
            }}
        """)
        alarm_input_layout.addWidget(self.time_edit)

        alarm_input_layout.addStretch()
        self.alarm_frame.setVisible(False)
        layout.addWidget(self.alarm_frame)

        self.heartbeat_frame = QFrame()
        hb_layout = QVBoxLayout(self.heartbeat_frame)
        hb_layout.setContentsMargins(0, 12, 0, 12)
        hb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.heart_widget = HeartWidget()
        hb_layout.addWidget(self.heart_widget, 0, Qt.AlignmentFlag.AlignCenter)

        self.bpm_label = QLabel("当前心跳: 72 BPM")
        self.bpm_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bpm_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS["text_primary"]};
            padding: 4px 0;
        """)
        hb_layout.addWidget(self.bpm_label)

        range_row = QHBoxLayout()
        range_row.setSpacing(8)

        min_label = QLabel("最小心跳:")
        min_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        range_row.addWidget(min_label)

        self.bpm_min_spin = QSpinBox()
        self.bpm_min_spin.setRange(30, 200)
        self.bpm_min_spin.setValue(self.bpm_min)
        self.bpm_min_spin.setFixedWidth(90)
        self.bpm_min_spin.valueChanged.connect(self._on_bpm_range_changed)
        self.bpm_min_spin.setStyleSheet("font-size: 14px;")
        range_row.addWidget(self.bpm_min_spin)

        sep_label = QLabel("~")
        sep_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        range_row.addWidget(sep_label)

        max_label = QLabel("最大心跳:")
        max_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        range_row.addWidget(max_label)

        self.bpm_max_spin = QSpinBox()
        self.bpm_max_spin.setRange(30, 200)
        self.bpm_max_spin.setValue(self.bpm_max)
        self.bpm_max_spin.setFixedWidth(90)
        self.bpm_max_spin.valueChanged.connect(self._on_bpm_range_changed)
        self.bpm_max_spin.setStyleSheet("font-size: 14px;")
        range_row.addWidget(self.bpm_max_spin)

        range_row.addStretch()
        hb_layout.addLayout(range_row)

        self.heartbeat_frame.setVisible(False)
        layout.addWidget(self.heartbeat_frame)

        self.ecg_widget = EcgWidget()
        self.ecg_widget.setVisible(False)
        layout.addWidget(self.ecg_widget)

        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(60)
        font.setBold(True)
        self.time_label.setFont(font)
        self.time_label.setStyleSheet(f"""
            color: {COLORS["text_primary"]};
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
                background-color: {COLORS["background"]};
                height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS["primary"]};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress)

        layout.addStretch()

        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 16, 0, 0)

        self.start_btn = QPushButton("开始")
        self.start_btn.setFixedHeight(40)
        self.start_btn.setStyleSheet(self._btn_style("#E74C3C", "#C0392B"))
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

    def _make_mode_btn(self, text, checked=False):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setFixedHeight(32)
        if checked:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS["primary"]};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
                }}
                QPushButton:checked {{
                    background-color: {COLORS["primary"]};
                }}
                QPushButton:!checked {{
                    background-color: white;
                    color: {COLORS["primary"]};
                    border: 1px solid {COLORS["primary"]};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: white;
                    color: {COLORS["primary"]};
                    border: 1px solid {COLORS["primary"]};
                    border-radius: 4px;
                    font-size: 12px;
                }}
                QPushButton:checked {{
                    background-color: {COLORS["primary"]};
                    color: white;
                    border: none;
                }}
                QPushButton:!checked {{
                    background-color: white;
                    color: {COLORS["primary"]};
                    border: 1px solid {COLORS["primary"]};
                }}
            """)
        return btn

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
        self._bpm_vary_timer.stop()
        self.heart_widget.set_beating(False)
        self.ecg_widget.stop()
        self.ecg_widget.clear()

        self.pomodoro_btn.setChecked(mode == "pomodoro")
        self.alarm_btn.setChecked(mode == "alarm")
        self.heartbeat_btn.setChecked(mode == "heartbeat")

        self.input_frame.setVisible(mode == "pomodoro")
        self.alarm_frame.setVisible(mode == "alarm")
        self.heartbeat_frame.setVisible(mode == "heartbeat")

        is_hb = (mode == "heartbeat")
        self.is_alarm = (mode == "alarm")
        self.is_heartbeat = is_hb
        self.ecg_widget.setVisible(is_hb)
        self.time_label.setVisible(not is_hb)
        self.progress.setVisible(not is_hb)

        self.reset_timer()

    def _on_bpm_range_changed(self):
        self.bpm_min = self.bpm_min_spin.value()
        self.bpm_max = self.bpm_max_spin.value()
        if self.bpm_min > self.bpm_max:
            if self.sender() == self.bpm_min_spin:
                self.bpm_max_spin.setValue(self.bpm_min)
                self.bpm_max = self.bpm_min
            else:
                self.bpm_min_spin.setValue(self.bpm_max)
                self.bpm_min = self.bpm_max
        mid = (self.bpm_min + self.bpm_max) // 2
        self.current_bpm = mid
        self.heart_widget.set_bpm(mid)
        self.ecg_widget.set_bpm(mid)
        self.bpm_label.setText(f"当前心跳: {mid} BPM")
        self.settings.set("bpm_min", self.bpm_min, True)
        self.settings.set("bpm_max", self.bpm_max, True)

    def toggle_timer(self):
        if self.is_running:
            self.pause_timer()
        else:
            self.start_timer()

    def start_timer(self):
        if self.is_running:
            return

        if self.is_heartbeat:
            mid = (self.bpm_min + self.bpm_max) // 2
            self.current_bpm = mid
            self.heart_widget.set_bpm(mid)
            self.heart_widget.set_beating(True)
            self.ecg_widget.set_bpm(mid)
            self.ecg_widget.show()
            self.time_label.hide()
            self.bpm_label.setText(f"当前心跳: {mid} BPM")
            self.ecg_widget.start()
            self._bpm_vary_timer.start(5000)
            self.is_running = True
            self.start_btn.setText("暂停")
            self.start_btn.setStyleSheet(self._btn_style("#F39C12", "#E67E22"))
            self.time_label.setText(f"{mid}")
            self.bpm_min_spin.setEnabled(False)
            self.bpm_max_spin.setEnabled(False)
            return

        if self.remaining_seconds == 0:
            if self.is_alarm:
                now = QTime.currentTime()
                alarm = self.time_edit.time()
                secs_now = now.hour() * 3600 + now.minute() * 60 + now.second()
                secs_alarm = alarm.hour() * 3600 + alarm.minute() * 60
                if secs_alarm <= secs_now:
                    secs_alarm += 24 * 3600
                self.total_seconds = secs_alarm - secs_now
                self.remaining_seconds = self.total_seconds
                self.alarm_armed = True
            else:
                self.total_seconds = self.minutes_value * 60
                self.remaining_seconds = self.total_seconds

        self.is_running = True
        self.timer.start(1000)
        self.start_btn.setText("暂停")
        self.start_btn.setStyleSheet(self._btn_style("#F39C12", "#E67E22"))
        self.increase_btn.setEnabled(False)
        self.decrease_btn.setEnabled(False)
        self.time_edit.setEnabled(False)

    def pause_timer(self):
        self.is_running = False

        if self.is_heartbeat:
            self.heart_widget.set_beating(False)
            self.ecg_widget.stop()
            self.ecg_widget.hide()
            self.time_label.show()
            self._bpm_vary_timer.stop()
            self.start_btn.setText("开始")
            self.start_btn.setStyleSheet(self._btn_style("#27AE60", "#229954"))
            self.bpm_min_spin.setEnabled(True)
            self.bpm_max_spin.setEnabled(True)
            return

        self.timer.stop()
        self.start_btn.setText("继续")
        self.start_btn.setStyleSheet(self._btn_style("#27AE60", "#229954"))

    def reset_timer(self):
        self.timer.stop()
        self._bpm_vary_timer.stop()
        self.heart_widget.set_beating(False)
        self.is_running = False
        self.alarm_armed = False

        if self.is_heartbeat:
            self.bpm_min = self.bpm_min_spin.value()
            self.bpm_max = self.bpm_max_spin.value()
            mid = (self.bpm_min + self.bpm_max) // 2
            self.current_bpm = mid
            self.heart_widget.set_bpm(mid)
            self.ecg_widget.set_bpm(mid)
            self.bpm_label.setText(f"当前心跳: {mid} BPM")
            self.time_label.setText(f"{mid}")
            self.progress.setValue(0)
            self.bpm_min_spin.setEnabled(True)
            self.bpm_max_spin.setEnabled(True)
        elif self.is_alarm:
            alarm = self.time_edit.time()
            self.alarm_time = alarm
            self.total_seconds = 0
            self.remaining_seconds = 0
            self.time_label.setText(alarm.toString("HH:mm"))
            self.progress.setValue(0)
            self.time_edit.setEnabled(True)
        else:
            self.total_seconds = self.minutes_value * 60
            self.remaining_seconds = self.total_seconds
            self.update_display()
            self.increase_btn.setEnabled(True)
            self.decrease_btn.setEnabled(True)
            self.time_edit.setEnabled(True)

        self.start_btn.setText("开始")
        self.start_btn.setStyleSheet(self._btn_style("#E74C3C", "#C0392B"))

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

    def _vary_bpm(self):
        new_bpm = random.randint(self.bpm_min, self.bpm_max)
        self.current_bpm = new_bpm
        self.heart_widget.set_bpm(new_bpm)
        self.ecg_widget.set_bpm(new_bpm)
        self.bpm_label.setText(f"当前心跳: {new_bpm} BPM")
        self.time_label.setText(f"{new_bpm}")

    def on_timer_finished(self):
        if self.is_alarm:
            if self.settings.get("play_sound", True):
                self._alarm_loop_active = True
                def _loop():
                    while self._alarm_loop_active:
                        self._play_alarm_once()
                        _time.sleep(3)
                _th.Thread(target=_loop, daemon=True).start()
            self.show_finish_dialog("闹铃时间到！", "关闭")
            self._alarm_loop_active = False
        else:
            if self.settings.get("play_sound", True):
                self._play_alarm_once()
            self.show_finish_dialog("时间到！", "确定")

    def _play_alarm_once(self):
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
        self._bpm_vary_timer.stop()
        self.heart_widget.cleanup()
        self.ecg_widget.stop()
        self._alarm_loop_active = False
        super().closeEvent(event)
