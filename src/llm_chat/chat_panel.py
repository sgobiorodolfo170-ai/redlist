from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QSplitter, QVBoxLayout, QWidget

from src.theme import COLORS
from src.llm_chat.chat_display import ChatDisplay
from src.llm_chat.conversation_list import ConversationList
from src.llm_chat.conversation_manager import ConversationManager
from src.llm_chat.input_bar import InputBar
from src.llm_chat.llm_service import LLMService
from src.utils.logger import get_logger

logger = get_logger("ChatPanel")


class ChatPanel(QWidget):
    def __init__(self, settings, main_window=None):
        super().__init__()
        self.settings = settings
        self.main_window = main_window
        self.conv_manager = ConversationManager(settings)
        self.current_conv_id = None
        self.current_messages = []
        self.llm_service = None
        self.accumulated_text = ""
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: white;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        main_frame = QFrame()
        main_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: none;
            }
        """)
        frame_layout = QVBoxLayout(main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(True)
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: #E9ECEF;
                width: 4px;
                margin: 0;
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS['primary']};
            }}
        """)

        self.conv_list = ConversationList(self.conv_manager)
        self.conv_list.setMinimumWidth(0)
        self.conv_list.conversation_selected.connect(self.on_conversation_selected)
        self.splitter.addWidget(self.conv_list)

        right_panel = QWidget()
        right_panel.setMinimumWidth(0)
        right_panel.setStyleSheet("background-color: white;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.right_splitter.setHandleWidth(4)
        self.right_splitter.setChildrenCollapsible(True)
        self.right_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: #E9ECEF;
                height: 4px;
                margin: 0;
            }}
            QSplitter::handle:hover {{
                background-color: {COLORS['primary']};
            }}
        """)

        self.chat_display = ChatDisplay()
        self.chat_display.collapse_toggled.connect(self.on_conv_list_collapse)
        self.chat_display.regenerate_requested.connect(self.on_regenerate_requested)
        self.right_splitter.addWidget(self.chat_display)

        self.input_bar = InputBar(self.settings, self.main_window)
        self.input_bar.send_signal.connect(self.on_send)
        self.input_bar.screenshot_requested.connect(self.on_screenshot_requested)
        self.right_splitter.addWidget(self.input_bar)

        self.right_splitter.setSizes([480, 160])
        right_layout.addWidget(self.right_splitter)

        self.splitter.addWidget(right_panel)
        self.splitter.setSizes([120, 480])

        frame_layout.addWidget(self.splitter)
        layout.addWidget(main_frame)

    def on_conv_list_collapse(self, collapsed):
        if collapsed:
            sizes = self.splitter.sizes()
            self._conv_list_expanded = sizes[0]
            self.splitter.setSizes([0, sum(sizes)])
        else:
            restore = getattr(self, '_conv_list_expanded', 120)
            sizes = self.splitter.sizes()
            self.splitter.setSizes([restore, sum(sizes) - restore])

    def on_conversation_selected(self, conv_id):
        if self.llm_service and self.llm_service.isRunning():
            self.llm_service.cancel()
            self.llm_service.wait(500)
            self.llm_service = None
            self.input_bar.send_btn.setEnabled(True)
            self.input_bar.input_edit.setEnabled(True)
            self.chat_display.finalize_temp_bubble()
        self.current_conv_id = conv_id
        data = self.conv_manager.get_conversation(conv_id)
        if data:
            self.current_messages = data.get('messages', [])
            model = data.get('model', {})
            self.chat_display.load_messages(self.current_messages)

            self.input_bar.reload_providers()
            for i in range(self.input_bar.model_combo.count()):
                d = self.input_bar.model_combo.itemData(i)
                if isinstance(d, dict) and d.get('name') == model.get('name'):
                    self.input_bar.model_combo.setCurrentIndex(i)
                    break

    def on_regenerate_requested(self):
        for i in range(len(self.current_messages) - 1, -1, -1):
            if self.current_messages[i]['role'] == 'assistant':
                del self.current_messages[i]
                break
        else:
            return

        last_user_content = None
        for msg in reversed(self.current_messages):
            if msg['role'] == 'user':
                last_user_content = msg['content']
                break
        if last_user_content is None:
            return

        self.chat_display.load_messages(self.current_messages)

        model_config = self.input_bar.get_selected_provider()
        if not model_config:
            return

        expert = self.input_bar.get_selected_expert()
        api_messages = []
        if expert:
            api_messages.append({"role": "system", "content": expert.get('system_prompt', '')})
        for msg in self.current_messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        self.chat_display.create_temp_bubble('assistant')
        self.chat_display.update_temp_bubble('思考中...')
        self.input_bar.send_btn.setEnabled(False)
        self.input_bar.input_edit.setEnabled(False)

        self.accumulated_text = ""
        self.llm_service = LLMService(api_messages, model_config)
        self.llm_service.chunk_received.connect(self.on_chunk_received)
        self.llm_service.finished.connect(self.on_llm_finished)
        self.llm_service.error.connect(self.on_llm_error)
        self.llm_service.start()

    def on_send(self, content, model_config):
        if not self.current_conv_id:
            self.current_conv_id = self.conv_manager.create_conversation(model_config)
            self.conv_list.current_id = self.current_conv_id
            self.conv_list.load_conversations()

        expert = self.input_bar.get_selected_expert()

        user_message = {"role": "user", "content": content}
        self.current_messages.append(user_message)

        self.chat_display.create_temp_bubble('user')
        if isinstance(content, str):
            self.chat_display.update_temp_bubble(content)
        elif isinstance(content, list):
            texts = [p.get('text', '') for p in content if p.get('type') == 'text']
            self.chat_display.update_temp_bubble('\n'.join(texts) + ('\n[图片]' if any(p.get('type') == 'image_url' for p in content) else ''))
        self.chat_display.finalize_temp_bubble()

        api_messages = []
        if expert:
            api_messages.append({"role": "system", "content": expert.get('system_prompt', '')})
        for msg in self.current_messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        self.chat_display.create_temp_bubble('assistant')
        self.chat_display.update_temp_bubble('思考中...')

        self.input_bar.send_btn.setEnabled(False)
        self.input_bar.input_edit.setEnabled(False)

        self.accumulated_text = ""
        self.llm_service = LLMService(api_messages, model_config)
        self.llm_service.chunk_received.connect(self.on_chunk_received)
        self.llm_service.finished.connect(self.on_llm_finished)
        self.llm_service.error.connect(self.on_llm_error)
        self.llm_service.start()

    def on_chunk_received(self, text):
        if self.sender() is not self.llm_service:
            return
        self.accumulated_text += text
        self.chat_display.update_temp_bubble(self.accumulated_text)

    def on_llm_finished(self, full_text):
        if self.sender() is not self.llm_service:
            return
        self.chat_display.finalize_temp_bubble()
        self.accumulated_text = ""
        if full_text:
            self.current_messages.append({"role": "assistant", "content": full_text})
            self.conv_manager.save_message(self.current_conv_id, self.current_messages)
            self.conv_list.load_conversations()
        self.input_bar.send_btn.setEnabled(True)
        self.input_bar.input_edit.setEnabled(True)
        self.input_bar.input_edit.setFocus()

    def on_llm_error(self, error_msg):
        if self.sender() is not self.llm_service:
            return
        self.chat_display.update_temp_bubble(f"\n\n[错误] {error_msg}")
        self.chat_display.finalize_temp_bubble()
        self.accumulated_text = ""
        self.input_bar.send_btn.setEnabled(True)
        self.input_bar.input_edit.setEnabled(True)
        self.input_bar.input_edit.setFocus()
        logger.error(f"LLM error: {error_msg}")

    def on_screenshot_requested(self):
        if self.main_window and hasattr(self.main_window, 'start_screenshot'):
            self.main_window.start_screenshot()

    def set_main_window(self, main_window):
        self.main_window = main_window
        self.input_bar.set_main_window(main_window)
