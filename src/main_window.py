import os
import sys

from PyQt6.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QStackedLayout, QVBoxLayout, QWidget

from src.theme import COLORS
from src.translation.translation_service import TranslationService
from src.utils.logger import get_logger

logger = get_logger("MainWindow")


class MainWindow(QWidget):
    show_window_signal = pyqtSignal()

    DOCK_CHECK_INTERVAL = 200
    MOUSE_CHECK_INTERVAL = 100

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.current_tool = 'task'

        self.dock_enabled = True
        self.is_docked = False
        self.is_dock_hidden = False
        self.dock_edge = None
        self.dock_locked = False

        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.check_dock)

        self.mouse_check_timer = QTimer()
        self.mouse_check_timer.timeout.connect(self.check_mouse_position)

        self.show_timer = QTimer()
        self.show_timer.setSingleShot(True)
        self.show_timer.timeout.connect(self.show_from_dock)

        self.animating = False

        self.task_panel = None
        self.screenshot_mgr = None
        self.sticky_mgr = None
        self.timer_panel = None
        self.screenshot_translate_panel = None
        self.settings_panel = None

        self._hide_timer = None
        self._show_timer = None

        self.init_ui()

        self._init_panels_timer = QTimer()
        self._init_panels_timer.setSingleShot(True)
        self._init_panels_timer.timeout.connect(self._init_panels)
        self._init_panels_timer.start(10)

        QTimer.singleShot(100, self._start_timers)

        logger.info("MainWindow initialized")

    def _init_panels(self):
        from src.screenshot import ScreenshotManager
        from src.screenshot_translate import ScreenshotTranslatePanel
        from src.settings_panel import SettingsPanel
        from src.sticky_note import StickyNoteManager
        from src.task_panel import TaskPanel
        from src.timer import TimerPanel

        try:
            self.task_panel = TaskPanel(self.settings)
            self.stack_layout.addWidget(self.task_panel)

            self.screenshot_mgr = ScreenshotManager(self.settings)
            self.screenshot_mgr.main_window = self

            self.sticky_mgr = StickyNoteManager(self.settings)
            self.sticky_mgr.set_main_window(self)
            self.stack_layout.addWidget(self.sticky_mgr.get_panel())

            self.timer_panel = TimerPanel(self.settings)
            self.stack_layout.addWidget(self.timer_panel)

            self.screenshot_translate_panel = ScreenshotTranslatePanel(self.settings, self.sticky_mgr, self)
            self.stack_layout.addWidget(self.screenshot_translate_panel)

            self.settings_panel = SettingsPanel(self.settings, self)
            self.stack_layout.addWidget(self.settings_panel)

            logger.debug("All panels initialized")
        except Exception as e:
            logger.exception(f"Failed to initialize panels: {e}")

    def _start_timers(self):
        self.hide_timer.start(self.DOCK_CHECK_INTERVAL)
        self.mouse_check_timer.start(self.MOUSE_CHECK_INTERVAL)
        logger.debug(f"Timers started: dock={self.DOCK_CHECK_INTERVAL}ms, mouse={self.MOUSE_CHECK_INTERVAL}ms")

    def init_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._set_window_icon()

        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card_bg']};
                border-radius: 8px;
                border: 1px solid #BDC3C7;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        title_bar = self.create_title_bar()
        title_bar.setFixedHeight(32)

        toolbar = self.create_toolbar()

        self.stack_layout = QStackedLayout()
        self.stack_layout.setContentsMargins(0, 0, 0, 0)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(title_bar)
        container_layout.addWidget(toolbar)
        container_layout.addLayout(self.stack_layout)

        self.stack_layout.setCurrentIndex(0)

        self.setFixedSize(320, 500)
        self.move_to_right()

    def _set_window_icon(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_path, 'app-icons', 'RedList.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def create_title_bar(self):
        title_bar = QFrame()
        title_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['primary']};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(8, 0, 8, 0)

        title = QLabel("RedList")
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        layout.addWidget(title)
        layout.addStretch()

        min_btn = QPushButton("─")
        min_btn.setFixedSize(24, 24)
        min_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,0.2);
                border-radius: 4px;
            }
        """)
        min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #C0392B;
                border-radius: 4px;
            }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.title_bar = title_bar
        self.drag_position = None

        title_bar.mousePressEvent = self.on_mouse_press
        title_bar.mouseMoveEvent = self.on_mouse_move
        title_bar.mouseReleaseEvent = self.on_mouse_release

        return title_bar

    def create_toolbar(self):
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background']};
                border-bottom: 1px solid #BDC3C7;
            }}
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(4, 4, 4, 4)

        tools = [
            ('task', '📖', '任务'),
            ('note', '📝', '便利贴'),
            ('timer', '⏱', '定时器'),
            ('translate', '🔤', '翻译'),
            ('settings', '⚙', '设置')
        ]

        self.tool_buttons = {}
        for tool_id, icon, tooltip in tools:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                    font-size: 18px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['hover']};
                }}
                QPushButton:checked {{
                    background-color: {COLORS['primary']};
                    color: white;
                }}
            """)
            btn.clicked.connect(lambda checked, t=tool_id: self.switch_tool(t))
            layout.addWidget(btn)
            self.tool_buttons[tool_id] = btn

        layout.addStretch()

        screenshot_btn = QPushButton('📷')
        screenshot_btn.setFixedSize(40, 40)
        screenshot_btn.setToolTip("截图")
        screenshot_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #D5DBDB;
            }
        """)
        screenshot_btn.clicked.connect(self.start_screenshot)
        layout.addWidget(screenshot_btn)

        self.tool_buttons['task'].setChecked(True)

        return toolbar

    def switch_tool(self, tool_id):
        for btn in self.tool_buttons.values():
            btn.setChecked(False)
        self.tool_buttons[tool_id].setChecked(True)

        tool_index = ['task', 'note', 'timer', 'translate', 'settings'].index(tool_id)
        if self.stack_layout.count() > tool_index:
            self.stack_layout.setCurrentIndex(tool_index)
        self.current_tool = tool_id

    def start_screenshot(self):
        if self.screenshot_mgr:
            self.screenshot_mgr.start_region_screenshot()

    def on_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.dock_enabled = False

    def on_mouse_move(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position:
            self.move(event.globalPosition().toPoint() - self.drag_position)

    def on_mouse_release(self, event):
        self.drag_position = None
        QTimer.singleShot(500, lambda: setattr(self, 'dock_enabled', True))

    def closeEvent(self, event):
        logger.info("MainWindow closing, cleaning up resources...")

        self._stop_timers()

        if self.task_panel and hasattr(self.task_panel, 'closeEvent'):
            self.task_panel.closeEvent(event)
        if self.screenshot_mgr and hasattr(self.screenshot_mgr, 'get_panel'):
            panel = self.screenshot_mgr.get_panel()
            if hasattr(panel, 'closeEvent'):
                panel.closeEvent(event)
        if self.sticky_mgr:
            self.sticky_mgr.cleanup()
        if self.timer_panel and hasattr(self.timer_panel, 'closeEvent'):
            self.timer_panel.closeEvent(event)
        if self.screenshot_translate_panel and hasattr(self.screenshot_translate_panel, 'closeEvent'):
            self.screenshot_translate_panel.closeEvent(event)
        if self.settings_panel and hasattr(self.settings_panel, 'closeEvent'):
            self.settings_panel.closeEvent(event)

        self.settings.flush()

        TranslationService.cleanup()

        logger.info("Application exiting")
        QApplication.quit()

    def _stop_timers(self):
        self.hide_timer.stop()
        self.mouse_check_timer.stop()
        self.show_timer.stop()

        if self._hide_timer:
            self._hide_timer.stop()
        if self._show_timer:
            self._show_timer.stop()

    def moveEvent(self, event):
        super().moveEvent(event)
        if self.sticky_mgr:
            self.sticky_mgr.update_magnet_notes_position()

    def check_dock(self):
        if self.dock_locked or not self.dock_enabled or self.isHidden() or self.animating:
            return

        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return

        geo = self.geometry()
        screen_geo = screen.availableGeometry()

        sensitivity = self.settings.get('dock_sensitivity', 5)

        docked = False
        self.dock_edge = None

        if geo.left() <= screen_geo.left() + sensitivity:
            docked = True
            self.dock_edge = 'left'

        if geo.right() >= screen_geo.right() - sensitivity:
            docked = True
            self.dock_edge = 'right'

        if geo.top() <= screen_geo.top() + sensitivity:
            docked = True
            self.dock_edge = 'top'

        if geo.bottom() >= screen_geo.bottom() - sensitivity:
            docked = True
            self.dock_edge = 'bottom'

        if docked and not self.is_docked:
            self.is_docked = True
            self.start_hide_animation()

    def check_mouse_position(self):
        try:
            if not self.is_dock_hidden or self.isVisible():
                return
        except RuntimeError:
            return

        try:
            from PyQt6.QtGui import QCursor
            pos = QCursor.pos()

            geo = self.geometry() if self.isVisible() else self._hide_rect
            if not geo:
                geo = self.geometry()
            trigger_size = 60

            in_trigger = False

            if self.dock_edge == 'left':
                if pos.x() <= geo.x() + trigger_size:
                    in_trigger = True
            elif self.dock_edge == 'right':
                if pos.x() >= geo.x() + geo.width() - trigger_size:
                    in_trigger = True
            elif self.dock_edge == 'top':
                if pos.y() <= geo.y() + trigger_size:
                    in_trigger = True
            elif self.dock_edge == 'bottom':
                if pos.y() >= geo.y() + geo.height() - trigger_size:
                    in_trigger = True

            if in_trigger:
                if not self.show_timer.isActive():
                    self.show_timer.start(100)
            else:
                self.show_timer.stop()
        except Exception as e:
            logger.error(f"Error in check_mouse_position: {e}")

    def start_hide_animation(self):
        if self.animating:
            return

        saved_edge = self.dock_edge

        self.animating = True
        geo = self.geometry()
        self._hide_rect = QRect(self.pos(), geo.size())
        self.dock_edge = saved_edge

        screen = self.screen()
        if screen:
            screen_geo = screen.availableGeometry()
            geo = self.geometry()

            x = self._hide_rect.x()
            y = self._hide_rect.y()

            if x <= screen_geo.left() + 10:
                x = screen_geo.left() + 15
            elif x + geo.width() >= screen_geo.right() - 10:
                x = screen_geo.right() - geo.width() - 15

            if y <= screen_geo.top() + 10:
                y = screen_geo.top() + 15
            elif y + geo.height() >= screen_geo.bottom() - 10:
                y = screen_geo.bottom() - geo.height() - 15

            self._hide_rect.setX(x)
            self._hide_rect.setY(y)

        self._hide_animation_step = 0
        if self._hide_timer:
            self._hide_timer.stop()
        self._hide_timer = QTimer()
        self._hide_timer.timeout.connect(self._animate_hide)
        self._hide_timer.start(15)

    def _animate_hide(self):
        self._hide_animation_step += 1
        current = self.pos()
        target = self._hide_rect.topLeft()

        dx = int((target.x() - current.x()) * 0.3)
        dy = int((target.y() - current.y()) * 0.3)

        if abs(dx) < 1 and abs(dy) < 1:
            self.move(target)
            self._hide_timer.stop()
            self.animating = False
            self.hide()
            self.is_docked = False
            self.is_dock_hidden = True
            if self.sticky_mgr:
                self.sticky_mgr.hide_magnet_notes()
        else:
            self.move(current.x() + dx, current.y() + dy)

    def show_from_dock(self):
        self.is_dock_hidden = False
        self.show()
        self.animating = True
        self._show_target = self.pos()

        self.dock_locked = True
        QTimer.singleShot(2000, lambda: setattr(self, 'dock_locked', False))

        screen = self.screen()
        if screen:
            screen_geo = screen.availableGeometry()
            geo = self.geometry()

            if self._show_target.x() < screen_geo.left():
                self._show_target.setX(screen_geo.left())
            elif self._show_target.x() + geo.width() > screen_geo.right():
                self._show_target.setX(screen_geo.right() - geo.width())

        self._show_animation_step = 0
        if self._show_timer:
            self._show_timer.stop()
        self._show_timer = QTimer()
        self._show_timer.timeout.connect(self._animate_show)
        self._show_timer.start(15)

    def _animate_show(self):
        self._show_animation_step += 1
        current = self.pos()
        target = self._show_target

        dx = int((target.x() - current.x()) * 0.4)
        dy = int((target.y() - current.y()) * 0.4)

        if abs(dx) < 1 and abs(dy) < 1:
            self.move(target)
            self._show_timer.stop()
            self.animating = False
            self.activateWindow()
        else:
            self.move(current.x() + dx, current.y() + dy)

    def enterEvent(self, event):
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)

    def move_to_right(self):
        screen = self.screen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = screen_geo.right() - self.width() - 20
            y = (screen_geo.height() - self.height()) // 2 + screen_geo.top()
            self.move(x, y)
