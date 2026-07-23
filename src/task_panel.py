import json
import uuid
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.theme import COLORS
from src.utils.logger import get_logger

logger = get_logger("TaskPanel")


class TaskCheckBox(QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked_color = "#27AE60"
        self._hover_color = "#E74C3C"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRect(0, 0, 20, 20)
        is_checked = self.isChecked()
        is_hover = self.underMouse()

        if is_checked:
            painter.setBrush(QColor("#27AE60"))
            painter.setPen(QColor("#27AE60"))
        else:
            painter.setBrush(QColor("white"))
            painter.setPen(QColor("#E74C3C" if is_hover else "#BDC3C7"))

        painter.drawEllipse(rect.adjusted(2, 2, -2, -2))

        if is_checked:
            painter.setPen(
                QPen(QColor("white"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            )
            check_rect = rect.adjusted(6, 6, -6, -6)
            painter.drawLine(check_rect.left(), check_rect.center().y(), check_rect.center().x(), check_rect.bottom())
            painter.drawLine(check_rect.center().x(), check_rect.bottom(), check_rect.right(), check_rect.top())

        painter.end()

    def sizeHint(self):
        from PyQt6.QtCore import QSize

        return QSize(20, 20)

    def minimumSizeHint(self):
        return self.sizeHint()


class TaskPanel(QWidget):
    task_changed = pyqtSignal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.tasks = []
        self.task_file = None

        self.init_ui()

        QTimer.singleShot(0, self._delayed_load)

    def _delayed_load(self):
        self.task_file = self._get_task_file_path()
        self.load_tasks()

    def _get_task_file_path(self):
        path = self.settings.get_tasks_path()
        Path(path).mkdir(parents=True, exist_ok=True)
        return Path(path) / "tasks.json"

    def refresh_path(self):
        self.task_file = self._get_task_file_path()
        self.load_tasks()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)

        # 标题 + 统计
        self.header_label = QLabel("任务清单")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {COLORS["text_primary"]};
            padding: 8px 0;
        """)
        layout.addWidget(self.header_label)

        # 任务列表
        self.task_list = QListWidget()
        self.task_list.setStyleSheet("""
            QListWidget {
                border: none;
                border-radius: 8px;
                background: #F0F0F0;
                outline: none;
            }
            QListWidget::item {
                padding: 0;
                background: transparent;
                border: none;
            }
            QListWidget::item:selected {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item:hover {
                background: transparent;
                border: none;
            }
        """)
        self.task_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.task_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.task_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self.task_list, 1)

        # 添加任务
        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("添加新任务...")
        self.task_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {COLORS["border"]};
                border-radius: 4px;
                padding: 10px;
                background: white;
                font-size: 13px;
                color: black;
            }}
            QLineEdit:focus {{
                border-color: {COLORS["primary"]};
            }}
        """)
        self.task_input.returnPressed.connect(self.add_task)
        add_layout.addWidget(self.task_input, 1)

        add_btn = QPushButton("+ 添加")
        add_btn.setFixedHeight(36)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["primary"]};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
        """)
        add_btn.clicked.connect(self.add_task)
        add_layout.addWidget(add_btn)

        layout.addLayout(add_layout)

    def load_tasks(self):
        if self.task_file.exists():
            try:
                with open(self.task_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = data.get("tasks", [])
            except Exception as e:
                logger.warning("Failed to load tasks from %s: %s", self.task_file, e)
                self.tasks = []
        else:
            self.tasks = []
        self.update_task_list()

    def save_tasks(self):
        Path(self.task_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.task_file, "w", encoding="utf-8") as f:
            json.dump({"tasks": self.tasks}, f, indent=2, ensure_ascii=False)

    def add_task(self):
        text = self.task_input.text().strip()
        if not text:
            return

        task = {"id": str(uuid.uuid4()), "text": text, "completed": False, "created_at": datetime.now().isoformat()}
        self.tasks.append(task)
        self.task_input.clear()
        self.save_tasks()
        self.update_task_list()

    def toggle_task(self, task_id):
        # 找到并切换任务状态
        task_to_move = None
        for task in self.tasks:
            if task["id"] == task_id:
                task["completed"] = not task["completed"]
                task_to_move = task
                break

        # 如果任务完成，移动到末尾
        if task_to_move and task_to_move["completed"]:
            self.tasks.remove(task_to_move)
            self.tasks.append(task_to_move)

        self.save_tasks()
        self.update_task_list()

    def delete_task(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        self.save_tasks()
        self.update_task_list()

    def update_task_list(self):
        self.task_list.clear()

        completed = sum(1 for t in self.tasks if t["completed"])
        total = len(self.tasks)
        self.header_label.setText(f"任务清单 ({completed}/{total} 完成)")

        for task in self.tasks:
            item = QListWidgetItem()
            widget = self.create_task_widget(task)
            item.setSizeHint(widget.sizeHint())
            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, widget)

    def create_task_widget(self, task):
        widget = QFrame()
        widget.setFixedHeight(52)
        widget.setCursor(Qt.CursorShape.PointingHandCursor)

        is_completed = task["completed"]
        bg_color = "#F0F0F0" if is_completed else "#FFFFFF"
        widget.setStyleSheet(f"""
            QFrame {{
                background: {bg_color};
                margin: 2px 2px;
                padding: 0;
                border: 1px solid #E74C3C;
                border-radius: 8px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 2)
        if not is_completed:
            widget.setGraphicsEffect(shadow)
        widget._shadow = shadow

        def enter_event(event):
            if not is_completed:
                widget.setStyleSheet("""
                    QFrame {
                        background: #FFFFFF;
                        margin: 2px 2px;
                        padding: 0;
                        border: 1px solid #E74C3C;
                        border-radius: 8px;
                    }
                """)
                shadow.setBlurRadius(12)
                shadow.setColor(QColor(230, 76, 60, 60))
                shadow.setOffset(0, 4)
            QFrame.enterEvent(widget, event)

        def leave_event(event):
            if not is_completed:
                widget.setStyleSheet("""
                    QFrame {
                        background: #FFFFFF;
                        margin: 2px 2px;
                        padding: 0;
                        border: 1px solid #E74C3C;
                        border-radius: 8px;
                    }
                """)
                shadow.setBlurRadius(8)
                shadow.setColor(QColor(0, 0, 0, 30))
                shadow.setOffset(0, 2)
            QFrame.leaveEvent(widget, event)

        widget.enterEvent = enter_event
        widget.leaveEvent = leave_event

        def double_click_event(event):
            if event.button() == Qt.MouseButton.LeftButton:
                checkbox.setChecked(not checkbox.isChecked())

        widget.mouseDoubleClickEvent = double_click_event

        main_layout = QHBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        color_bar = QFrame()
        color_bar.setFixedWidth(4)
        bar_color = "#27AE60" if is_completed else "#E74C3C"
        color_bar.setStyleSheet(f"""
            QFrame {{
                background: {bar_color};
                border: none;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
            }}
        """)
        main_layout.addWidget(color_bar)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(12, 8, 12, 8)
        content_layout.setSpacing(12)

        checkbox = TaskCheckBox()
        checkbox.setChecked(is_completed)
        checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        checkbox.stateChanged.connect(lambda state: self.toggle_task(task["id"]))
        content_layout.addWidget(checkbox)

        label = QLabel(task["text"])
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_color = "#95A5A6" if is_completed else "#2C3E50"
        font_style = "font-size: 15px;"
        if is_completed:
            font_style += " text-decoration: line-through;"
        label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                {font_style}
                background: transparent;
                border: none;
            }}
        """)
        content_layout.addWidget(label, 1)

        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #BDC3C7;
                border: none;
                font-size: 18px;
                font-weight: bold;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: #FDEDEC;
                color: #E74C3C;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_task(task["id"]))
        content_layout.addWidget(delete_btn)

        main_layout.addLayout(content_layout)

        return widget
