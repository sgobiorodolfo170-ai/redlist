import glob
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.theme import COLORS
from src.utils.logger import get_logger
from src.utils.sound import play_sound

logger = get_logger("SettingsPanel")


class SettingsPanel(QWidget):
    def __init__(self, settings, main_window):
        super().__init__()
        self.settings = settings
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: white;
            }}
            QLabel {{
                color: {COLORS["text_primary"]};
                font-size: 13px;
            }}
            QSpinBox, QLineEdit {{
                border: none;
                border-radius: 4px;
                padding: 4px 6px;
                background-color: {COLORS["background"]};
                color: {COLORS["text_primary"]};
                font-size: 12px;
                min-height: 24px;
            }}
            QSpinBox:focus, QLineEdit:focus {{
                background-color: {COLORS["hover"]};
            }}
            QComboBox {{
                border: none;
                border-radius: 4px;
                padding: 4px 6px;
                background-color: {COLORS["background"]};
                color: {COLORS["text_primary"]};
                font-size: 12px;
                min-height: 24px;
            }}
            QComboBox:focus {{
                background-color: {COLORS["hover"]};
            }}
            QComboBox::drop-down {{
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {COLORS["border"]};
                background-color: white;
                selection-background-color: {COLORS["hover"]};
            }}
            QCheckBox {{
                color: {COLORS["text_primary"]};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid {COLORS["border"]};
                border-radius: 4px;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid {COLORS["primary"]};
                border-radius: 4px;
                background-color: {COLORS["primary"]};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS["primary"]};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)

        header = QLabel("设置")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS["text_primary"]};
            padding: 8px 0;
        """)
        layout.addWidget(header)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setHorizontalSpacing(8)
        form_layout.setVerticalSpacing(12)

        sensitivity = QSpinBox()
        sensitivity.setRange(1, 20)
        sensitivity.setFixedWidth(80)
        sensitivity.setValue(self.settings.get("dock_sensitivity", 5))
        sensitivity.valueChanged.connect(lambda v: self.settings.set("dock_sensitivity", v))

        auto_start_check = QCheckBox("开机启动")
        auto_start_check.setChecked(self.settings.get("auto_start", False))
        auto_start_check.toggled.connect(self._on_auto_start_changed)

        sensitivity_layout = QHBoxLayout()
        sensitivity_layout.setSpacing(16)
        sensitivity_layout.addWidget(sensitivity)
        sensitivity_layout.addWidget(auto_start_check)
        sensitivity_layout.addStretch()
        form_layout.addRow("停靠灵敏度:", sensitivity_layout)

        minimize_tray_check = QCheckBox("关闭时存入托盘")
        minimize_tray_check.setChecked(self.settings.get("minimize_to_tray", True))
        minimize_tray_check.toggled.connect(self._on_minimize_to_tray_changed)
        sensitivity_layout.addWidget(minimize_tray_check)

        screenshot_edit = QLineEdit()
        screenshot_edit.setText(self.settings.get_screenshot_path())
        screenshot_edit.textChanged.connect(lambda v: self.settings.set("screenshot_path", v))
        screenshot_btn = self._create_browse_btn()
        screenshot_btn.clicked.connect(
            lambda: self._browse_folder(
                screenshot_edit, "截图保存路径", lambda v: self.settings.set("screenshot_path", v)
            )
        )
        screenshot_layout = QHBoxLayout()
        screenshot_layout.setSpacing(6)
        screenshot_layout.addWidget(screenshot_edit, 1)
        screenshot_layout.addWidget(screenshot_btn)
        form_layout.addRow("截图路径:", screenshot_layout)

        recording_edit = QLineEdit()
        recording_edit.setText(self.settings.get_recording_path())
        recording_edit.textChanged.connect(lambda v: self.settings.set("recording_path", v))
        recording_btn = self._create_browse_btn()
        recording_btn.clicked.connect(
            lambda: self._browse_folder(
                recording_edit, "录屏保存路径", lambda v: self.settings.set("recording_path", v)
            )
        )
        recording_layout = QHBoxLayout()
        recording_layout.setSpacing(6)
        recording_layout.addWidget(recording_edit, 1)
        recording_layout.addWidget(recording_btn)
        form_layout.addRow("录屏路径:", recording_layout)

        self.data_path_edit = QLineEdit()
        self.data_path_edit.setText(self.settings.get_data_path())
        self.data_path_edit.textChanged.connect(self._on_data_path_changed)
        data_browse_btn = self._create_browse_btn()
        data_browse_btn.clicked.connect(self._browse_data_folder)
        data_layout = QHBoxLayout()
        data_layout.setSpacing(6)
        data_layout.addWidget(self.data_path_edit, 1)
        data_layout.addWidget(data_browse_btn)
        form_layout.addRow("数据路径:", data_layout)

        sound_check = QCheckBox("定时结束播放提示音")
        sound_check.setChecked(self.settings.get("play_sound", True))
        sound_check.toggled.connect(lambda v: self.settings.set("play_sound", v))
        form_layout.addRow("", sound_check)

        self.alarm_combo = QComboBox()
        self._load_sounds()
        self.alarm_combo.currentTextChanged.connect(lambda v: self.settings.set("alarm_sound", v))
        test_btn = QPushButton("试听")
        test_btn.setFixedSize(50, 28)
        test_btn.setStyleSheet(self._button_style())
        test_btn.clicked.connect(self._test_sound)
        alarm_layout = QHBoxLayout()
        alarm_layout.setSpacing(6)
        alarm_layout.addWidget(self.alarm_combo, 1)
        alarm_layout.addWidget(test_btn)
        form_layout.addRow("提示铃声:", alarm_layout)

        layout.addLayout(form_layout)
        layout.addStretch()

    def _create_browse_btn(self):
        btn = QPushButton("...")
        btn.setFixedSize(36, 28)
        btn.setStyleSheet(self._button_style())
        return btn

    def _button_style(self):
        return f"""
            QPushButton {{
                background-color: {COLORS["background"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                font-size: 12px;
                color: {COLORS["text_primary"]};
            }}
            QPushButton:hover {{
                background-color: {COLORS["hover"]};
                border-color: {COLORS["primary"]};
            }}
        """

    def _browse_folder(self, edit, title, on_change):
        folder = QFileDialog.getExistingDirectory(self, f"选择{title}", edit.text())
        if folder:
            edit.setText(folder)
            on_change(folder)

    def _on_data_path_changed(self, v):
        self.settings.set("data_path", v)
        if self.main_window.task_panel:
            self.main_window.task_panel.refresh_path()
        if self.main_window.sticky_mgr:
            self.main_window.sticky_mgr.refresh_path()

    def _browse_data_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择数据保存文件夹", self.data_path_edit.text() or self.settings.get_data_path()
        )
        if folder:
            self.data_path_edit.setText(folder)

    def _on_auto_start_changed(self, checked):
        self.settings.set("auto_start", checked)
        from src.settings import set_auto_start

        set_auto_start(checked)

    def _on_minimize_to_tray_changed(self, checked):
        self.settings.set("minimize_to_tray", checked)

    def _load_sounds(self):
        sounds_dir = self.settings.get_sounds_dir()
        sound_files = glob.glob(os.path.join(sounds_dir, "*.mid")) + glob.glob(os.path.join(sounds_dir, "*.mp3"))
        if sound_files:
            for sound_file in sound_files:
                self.alarm_combo.addItem(os.path.basename(sound_file))
            current_sound = self.settings.get_alarm_sound()
            idx = self.alarm_combo.findText(current_sound)
            if idx >= 0:
                self.alarm_combo.setCurrentIndex(idx)
        else:
            self.alarm_combo.addItem("alert-sound-on-mobile-phone.mp3")

    def _test_sound(self):
        try:
            sounds_dir = self.settings.get_sounds_dir()
            sound_path = os.path.join(sounds_dir, self.alarm_combo.currentText())
            if os.path.exists(sound_path):
                play_sound(sound_path)
        except Exception as e:
            logger.warning("Failed to test sound: %s", e)
