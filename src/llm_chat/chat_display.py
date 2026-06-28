import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextBlockFormat, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.theme import COLORS
from src.utils.logger import get_logger

logger = get_logger("ChatDisplay")


class ChatDisplay(QScrollArea):
    collapse_toggled = pyqtSignal(bool)
    regenerate_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.temp_bubble = None
        self.temp_role = None
        self.temp_toolbar = None
        self._assistant_toolbars = []
        self._collapsed = False
        self.init_ui()

    def init_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #DEE2E6;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #BDC3C7;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        self.container = QWidget()
        self.container.setStyleSheet("background-color: white;")
        self.chat_layout = QVBoxLayout(self.container)
        self.chat_layout.setContentsMargins(12, 12, 12, 12)
        self.chat_layout.setSpacing(9)
        self.chat_layout.addStretch()

        self.setWidget(self.container)

        self.collapse_btn = QPushButton("◀", self.viewport())
        self.collapse_btn.setFixedSize(24, 24)
        self.collapse_btn.move(4, 4)
        self.collapse_btn.setToolTip("折叠会话列表")
        self.collapse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(248,249,250,200);
                color: {COLORS["text_secondary"]};
                border: 1px solid #E9ECEF;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {COLORS["hover"]};
            }}
        """)
        self.collapse_btn.clicked.connect(self.on_toggle_collapse)
        self.collapse_btn.raise_()

        self.welcome_label = QLabel("选择或新建一个会话开始对话")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setStyleSheet(f"""
            font-size: 14px;
            color: {COLORS["text_secondary"]};
            background: transparent;
            padding: 40px;
        """)
        self.chat_layout.insertWidget(0, self.welcome_label)

    def clear_messages(self):
        self._assistant_toolbars.clear()
        while self.chat_layout.count() > 0:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.chat_layout.addStretch()

        self.welcome_label = QLabel("选择或新建一个会话开始对话")
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setStyleSheet(f"""
            font-size: 14px;
            color: {COLORS["text_secondary"]};
            background: transparent;
            padding: 40px;
        """)
        self.chat_layout.insertWidget(0, self.welcome_label)

    def load_messages(self, messages):
        self.clear_messages()
        self.welcome_label.hide()
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            self.append_message(role, content)

    def _bubble_width(self):
        return int(self.viewport().width() * 0.85)

    def _make_bubble(self, role):
        bubble = QTextBrowser()
        bubble.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bubble.setOpenExternalLinks(True)
        bubble.setLineWrapMode(QTextBrowser.LineWrapMode.WidgetWidth)
        bubble.document().setDocumentMargin(0)
        bubble.document().setDefaultStyleSheet("p, body { margin: 0; }")

        padding_v = 9

        bubble._padding_top = padding_v
        bubble._padding_bottom = padding_v

        if role == "user":
            max_w = self._bubble_width()
            bubble.setMaximumWidth(max_w)
            bubble._text_width = max_w - 24
            bubble.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: {COLORS["primary"]};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: {padding_v}px 12px;
                    font-size: 16px;
                }}
            """)
        else:
            bubble._text_width = self.viewport().width() - 50
            bubble.setStyleSheet(f"""
                QTextBrowser {{
                    background-color: #FFFFFF;
                    color: {COLORS["text_primary"]};
                    border: 1px solid #E9ECEF;
                    border-radius: 8px;
                    padding: {padding_v}px 12px;
                    font-size: 16px;
                }}
            """)
        return bubble

    def _set_bubble_height(self, bubble):
        w = getattr(bubble, "_text_width", self.viewport().width() - 50)
        bubble.document().setTextWidth(w)
        padding_top = getattr(bubble, "_padding_top", 0)
        padding_bottom = getattr(bubble, "_padding_bottom", 0)
        h = bubble.document().size().height() + padding_top + padding_bottom
        h = max(h, 40)
        bubble.setFixedHeight(int(h))

    @staticmethod
    def _clean_document_spacing(doc):
        doc_root = doc.rootFrame()
        if doc_root:
            fmt = doc_root.frameFormat()
            fmt.setTopMargin(0)
            fmt.setBottomMargin(0)
            doc_root.setFrameFormat(fmt)
        block = doc.begin()
        bfmt = QTextBlockFormat()
        bfmt.setTopMargin(0)
        bfmt.setBottomMargin(0)
        cursor = QTextCursor(doc)
        while block.isValid():
            cursor.setPosition(block.position())
            cursor.mergeBlockFormat(bfmt)
            block = block.next()

    def _make_toolbar(self, bubble):
        toolbar = QWidget()
        toolbar.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        btn_style = """
            QPushButton {
                font-size: 12px;
                color: #7F8C8D;
                background-color: #F0F0F0;
                border: none;
                border-radius: 4px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
                color: #2C3E50;
            }
        """

        copy_btn = QPushButton("复制")
        copy_btn.setStyleSheet(btn_style)
        copy_btn.clicked.connect(lambda: self._on_copy_text(bubble._raw_text))
        layout.addWidget(copy_btn)

        export_btn = QPushButton("导出")
        export_btn.setStyleSheet(btn_style)
        export_btn.clicked.connect(lambda: self._on_export_md(bubble._raw_text))
        layout.addWidget(export_btn)

        regen_btn = QPushButton("重新生成")
        regen_btn.setStyleSheet(btn_style)
        regen_btn.clicked.connect(lambda: self._on_regen_request(toolbar))
        layout.addWidget(regen_btn)

        layout.addStretch()

        self._assistant_toolbars.append(toolbar)
        return toolbar

    def _on_copy_text(self, text):
        if isinstance(text, str):
            QApplication.clipboard().setText(text)

    def _on_export_md(self, text):
        if not isinstance(text, str):
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出为 Markdown", "untitled.md", "Markdown (*.md)")
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)
            except Exception:
                pass

    def _on_regen_request(self, toolbar):
        if self._assistant_toolbars and toolbar is self._assistant_toolbars[-1]:
            self.regenerate_requested.emit()

    def append_message(self, role, content):
        self.welcome_label.hide()
        text = self._format_content(content) if isinstance(content, str) else self._format_multimodal(content)
        bubble = self._make_bubble(role)
        bubble._raw_text = content if isinstance(content, str) else str(content)
        bubble.setHtml(text)
        bubble.document().setDocumentMargin(0)
        self._clean_document_spacing(bubble.document())

        wrapper = QVBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(2)

        hwrapper = QHBoxLayout()
        hwrapper.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            hwrapper.addStretch()
            hwrapper.addWidget(bubble)
        else:
            hwrapper.addWidget(bubble)
        wrapper.addLayout(hwrapper)

        if role == "assistant":
            toolbar = self._make_toolbar(bubble)
            wrapper.addWidget(toolbar)

        wrapper_widget = QWidget()
        wrapper_widget.setStyleSheet("background: transparent;")
        wrapper_widget.setLayout(wrapper)

        idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(idx, wrapper_widget)

        self._set_bubble_height(bubble)
        self.scroll_to_bottom()

    def create_temp_bubble(self, role):
        self.welcome_label.hide()
        self.temp_role = role
        self.temp_bubble = self._make_bubble(role)
        self.temp_bubble._raw_text = ""
        self.temp_bubble.setHtml("")
        self.temp_bubble.document().setDocumentMargin(0)
        self._clean_document_spacing(self.temp_bubble.document())

        wrapper = QVBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(2)

        hwrapper = QHBoxLayout()
        hwrapper.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            hwrapper.addStretch()
            hwrapper.addWidget(self.temp_bubble)
        else:
            hwrapper.addWidget(self.temp_bubble)
        wrapper.addLayout(hwrapper)

        if role == "assistant":
            self.temp_toolbar = self._make_toolbar(self.temp_bubble)
            self.temp_toolbar.hide()
            wrapper.addWidget(self.temp_toolbar)

        wrapper_widget = QWidget()
        wrapper_widget.setStyleSheet("background: transparent;")
        wrapper_widget.setLayout(wrapper)

        idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(idx, wrapper_widget)

        self.temp_bubble.setFixedHeight(40)
        self.scroll_to_bottom()

    def update_temp_bubble(self, text):
        if self.temp_bubble is None:
            return
        try:
            new_html = self._format_content(text)
            self.temp_bubble.setHtml(new_html)
            self.temp_bubble.document().setDocumentMargin(0)
            self._clean_document_spacing(self.temp_bubble.document())
            self._set_bubble_height(self.temp_bubble)
            self.scroll_to_bottom()
        except RuntimeError:
            logger.warning("RuntimeError in update_temp_bubble")
            self.temp_bubble = None

    def finalize_temp_bubble(self):
        if self.temp_toolbar is not None:
            self.temp_toolbar.show()
            self.temp_toolbar = None
        self.temp_bubble = None
        self.temp_role = None

    def on_toggle_collapse(self):
        self._collapsed = not self._collapsed
        self.collapse_btn.setText("▶" if self._collapsed else "◀")
        self.collapse_btn.setToolTip("展开会话列表" if self._collapsed else "折叠会话列表")
        self.collapse_toggled.emit(self._collapsed)

    def scroll_to_bottom(self):
        scrollbar = self.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def _format_content(self, text):
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.strip("\n")
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("\n", "<br>")
        code_block_pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
        text = code_block_pattern.sub(self._replace_code_block, text)
        inline_code = re.compile(r"`([^`]+)`")
        text = inline_code.sub(
            r'<code style="background:#E8E8E8;padding:2px 6px;border-radius:4px;font-size:12px;">\1</code>', text
        )
        bold = re.compile(r"\*\*(.+?)\*\*")
        text = bold.sub(r"<b>\1</b>", text)
        return f"<div style='margin:0;padding:0;'>{text}</div>"

    def _replace_code_block(self, match):
        lang = match.group(1) or ""
        code = match.group(2)
        code = code.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        escaped_code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lang_label = f'<div style="font-size:11px;color:#7F8C8D;margin-bottom:4px;">{lang}</div>' if lang else ""
        return (
            f'<div style="background:#2C3E50;color:#ECF0F1;border-radius:6px;padding:10px;'
            f'margin:8px 0;font-family:Consolas,monospace;font-size:12px;white-space:pre-wrap;">'
            f"{lang_label}{escaped_code}</div>"
        )

    def _format_multimodal(self, content_parts):
        text = ""
        for part in content_parts:
            if part.get("type") == "text":
                text += part.get("text", "")
            elif part.get("type") == "image_url":
                text += "[图片]"
        return self._format_content(text)
