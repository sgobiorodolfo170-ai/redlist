import datetime
import os
import sys

from PyQt6.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    mss = None

from src.ocr.ocr_service import OCRService
from src.overlay.mask_overlay import MaskTranslationOverlay
from src.screenshot.region_selector import RegionSelector
from src.screenshot.translation_thread import TranslationThread
from src.theme import COLORS
from src.translation.translation_service import TranslationService
from src.utils.color import darken_color, lighten_color
from src.utils.logger import get_logger

logger = get_logger("ScreenshotTranslate")

ERROR_LOG = "报错日志.md"


def _write_error_log(msg: str):
    try:
        log_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
        log_path = os.path.join(log_dir, ERROR_LOG)
        entry = (
            f"# 报错日志\n\n"
            f"- **时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **错误**: {msg}\n\n---\n\n"
        )
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


class ScreenshotTranslatePanel(QWidget):
    _ocr_loaded_signal = pyqtSignal(bool)

    def __init__(self, settings, sticky_manager=None, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.sticky_manager = sticky_manager
        self.selector = None
        self.ocr_service = OCRService()
        self.translation_service = TranslationService(settings)
        self.translation_overlay = None
        self.mask_translation_overlay = None
        self.last_text_blocks: list = []
        self.last_screenshot_rect = None
        self.translation_thread = None

        self._ocr_load_timer = QTimer()
        self._ocr_load_timer.setSingleShot(True)
        self._ocr_load_timer.timeout.connect(self._do_load_ocr)
        self._ocr_loaded_signal.connect(self._on_ocr_loaded)

        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(f"""
            QWidget {{
                background-color: white;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
            }}
            QLineEdit {{
                border: none;
                border-radius: 6px;
                padding: 10px 12px;
                background-color: #F5F5F5;
                color: {COLORS['text_primary']};
                font-size: 13px;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                background-color: #E8E8E8;
            }}
            QLineEdit::placeholder {{
                color: #ADB5BD;
            }}
            QComboBox {{
                border: none;
                border-radius: 6px;
                padding: 10px 12px;
                background-color: #F5F5F5;
                color: {COLORS['text_primary']};
                font-size: 13px;
                min-height: 20px;
            }}
            QComboBox:focus {{
                background-color: #E8E8E8;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 28px;
            }}
            QComboBox::down-arrow {{
                width: 14px;
                height: 14px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #DEE2E6;
                background-color: white;
                selection-background-color: {COLORS['hover']};
                selection-color: {COLORS['text_primary']};
                padding: 4px;
            }}
            QCheckBox {{
                spacing: 10px;
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
            }}
            QCheckBox::indicator:unchecked {{
                border: 2px solid #DEE2E6;
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                border: 2px solid {COLORS['primary']};
                background-color: {COLORS['primary']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS['primary']};
            }}
            QToolTip {{
                background-color: white;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                padding: 12px 16px;
                color: {COLORS['text_primary']};
                font-size: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(16)

        self.translate_btn = QPushButton("截图翻译")
        self.translate_btn.setFixedHeight(44)
        self.translate_btn.setEnabled(False)
        self.translate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.translate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #C0392B;
            }}
            QPushButton:pressed {{
                background-color: #A93226;
            }}
            QPushButton:disabled {{
                background-color: #BDC3C7;
                color: #F8F9FA;
            }}
        """)
        self.translate_btn.clicked.connect(self._start_translate)
        layout.addWidget(self.translate_btn)

        provider_group = QFrame()
        provider_group.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E9ECEF;
                border-radius: 12px;
            }
        """)
        provider_layout = QVBoxLayout(provider_group)
        provider_layout.setContentsMargins(16, 14, 16, 14)
        provider_layout.setSpacing(12)

        provider_header = QLabel("服务商选择")
        provider_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50;")
        provider_layout.addWidget(provider_header)

        provider_row = QHBoxLayout()
        provider_row.setSpacing(12)

        provider_label = QLabel("翻译服务商")
        provider_label.setStyleSheet("font-size: 13px; color: #495057;")
        provider_label.setFixedWidth(85)
        provider_row.addWidget(provider_label)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("百度大模型文本翻译", "baidu_llm")
        self.provider_combo.addItem("百度通用文本翻译", "baidu_nmt")
        self.provider_combo.addItem("腾讯翻译君", "tencent")

        current_provider = self.settings.get('translate_provider', 'baidu_llm')
        idx = self.provider_combo.findData(current_provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_row.addWidget(self.provider_combo, 1)

        help_btn = QPushButton("?")
        help_btn.setFixedSize(24, 24)
        help_btn.setCursor(Qt.CursorShape.WhatsThisCursor)
        help_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                font-size: 13px;
                font-weight: bold;
                color: {COLORS['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
                color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """)
        help_btn.setToolTip(
            "📊 服务对比：\n\n"
            "百度大模型文本翻译：\n"
            "  • 基于大模型，翻译更精准自然\n"
            "  • 支持翻译指令、术语库\n"
            "  • 推荐：高质量翻译场景\n\n"
            "百度通用文本翻译：\n"
            "  • 传统机器翻译，速度快\n"
            "  • 免费额度：200万字符/月\n"
            "  • 推荐：日常大量翻译\n\n"
            "腾讯翻译君：\n"
            "  • 免费额度：580万字符/月\n"
            "  • 支持语言：中、英、日、韩等\n"
            "  • 推荐：日常使用"
        )
        provider_row.addWidget(help_btn)

        provider_layout.addLayout(provider_row)
        layout.addWidget(provider_group)

        config_group = QFrame()
        config_group.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #E9ECEF;
                border-radius: 12px;
            }
        """)
        config_layout = QVBoxLayout(config_group)
        config_layout.setContentsMargins(16, 14, 16, 14)
        config_layout.setSpacing(12)

        config_header_row = QHBoxLayout()
        config_header_row.setSpacing(12)

        config_header = QLabel("API 密钥配置")
        config_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #2C3E50;")
        config_header_row.addWidget(config_header)

        config_header_row.addStretch()

        show_key_check = QCheckBox("显示密钥")
        show_key_check.setChecked(False)
        show_key_check.toggled.connect(lambda checked: (
            self.baidu_llm_key_edit.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password),
            self.baidu_nmt_key_edit.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password),
            self.tencent_key_edit.setEchoMode(QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password)
        ))
        config_header_row.addWidget(show_key_check)

        config_layout.addLayout(config_header_row)

        self.tencent_frame = QFrame()
        tencent_layout = QVBoxLayout(self.tencent_frame)
        tencent_layout.setContentsMargins(0, 0, 0, 0)
        tencent_layout.setSpacing(12)

        tencent_id_row = QHBoxLayout()
        tencent_id_row.setSpacing(12)

        tencent_id_label = QLabel("Secret ID")
        tencent_id_label.setStyleSheet("font-size: 13px; color: #495057; font-weight: 500;")
        tencent_id_label.setFixedWidth(85)
        tencent_id_row.addWidget(tencent_id_label)

        self.tencent_id_edit = QLineEdit()
        self.tencent_id_edit.setPlaceholderText("输入腾讯云 Secret ID")
        self.tencent_id_edit.setText(self.settings.get('tencent_secret_id', '').strip())
        self.tencent_id_edit.textChanged.connect(lambda v: self.settings.set('tencent_secret_id', v.strip()))
        tencent_id_row.addWidget(self.tencent_id_edit, 1)

        tencent_layout.addLayout(tencent_id_row)

        tencent_key_row = QHBoxLayout()
        tencent_key_row.setSpacing(12)

        tencent_key_label = QLabel("Secret Key")
        tencent_key_label.setStyleSheet("font-size: 13px; color: #495057; font-weight: 500;")
        tencent_key_label.setFixedWidth(85)
        tencent_key_row.addWidget(tencent_key_label)

        self.tencent_key_edit = QLineEdit()
        self.tencent_key_edit.setPlaceholderText("输入腾讯云 Secret Key")
        self.tencent_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.tencent_key_edit.setText(self.settings.get('tencent_secret_key', '').strip())
        self.tencent_key_edit.textChanged.connect(lambda v: self.settings.set('tencent_secret_key', v.strip()))
        tencent_key_row.addWidget(self.tencent_key_edit, 1)

        tencent_layout.addLayout(tencent_key_row)

        config_layout.addWidget(self.tencent_frame)

        self.baidu_llm_frame = QFrame()
        baidu_llm_layout = QVBoxLayout(self.baidu_llm_frame)
        baidu_llm_layout.setContentsMargins(0, 0, 0, 0)
        baidu_llm_layout.setSpacing(12)

        baidu_llm_id_row = QHBoxLayout()
        baidu_llm_id_row.setSpacing(12)
        baidu_llm_id_label = QLabel("App ID")
        baidu_llm_id_label.setStyleSheet("font-size: 13px; color: #495057; font-weight: 500;")
        baidu_llm_id_label.setFixedWidth(85)
        baidu_llm_id_row.addWidget(baidu_llm_id_label)
        self.baidu_llm_id_edit = QLineEdit()
        self.baidu_llm_id_edit.setPlaceholderText("输入百度大模型 App ID")
        self.baidu_llm_id_edit.setText(self.settings.get('baidu_llm_app_id', '').strip())
        self.baidu_llm_id_edit.textChanged.connect(lambda v: self.settings.set('baidu_llm_app_id', v.strip()))
        baidu_llm_id_row.addWidget(self.baidu_llm_id_edit, 1)
        baidu_llm_layout.addLayout(baidu_llm_id_row)

        baidu_llm_key_row = QHBoxLayout()
        baidu_llm_key_row.setSpacing(12)
        baidu_llm_key_label = QLabel("App Key")
        baidu_llm_key_label.setStyleSheet("font-size: 13px; color: #495057; font-weight: 500;")
        baidu_llm_key_label.setFixedWidth(85)
        baidu_llm_key_row.addWidget(baidu_llm_key_label)
        self.baidu_llm_key_edit = QLineEdit()
        self.baidu_llm_key_edit.setPlaceholderText("输入百度大模型 App Key")
        self.baidu_llm_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.baidu_llm_key_edit.setText(self.settings.get('baidu_llm_app_key', '').strip())
        self.baidu_llm_key_edit.textChanged.connect(lambda v: self.settings.set('baidu_llm_app_key', v.strip()))
        baidu_llm_key_row.addWidget(self.baidu_llm_key_edit, 1)
        baidu_llm_layout.addLayout(baidu_llm_key_row)

        config_layout.addWidget(self.baidu_llm_frame)

        self.baidu_nmt_frame = QFrame()
        baidu_nmt_layout = QVBoxLayout(self.baidu_nmt_frame)
        baidu_nmt_layout.setContentsMargins(0, 0, 0, 0)
        baidu_nmt_layout.setSpacing(12)

        baidu_nmt_id_row = QHBoxLayout()
        baidu_nmt_id_row.setSpacing(12)
        baidu_nmt_id_label = QLabel("App ID")
        baidu_nmt_id_label.setStyleSheet("font-size: 13px; color: #495057; font-weight: 500;")
        baidu_nmt_id_label.setFixedWidth(85)
        baidu_nmt_id_row.addWidget(baidu_nmt_id_label)
        self.baidu_nmt_id_edit = QLineEdit()
        self.baidu_nmt_id_edit.setPlaceholderText("输入百度通用 App ID")
        self.baidu_nmt_id_edit.setText(self.settings.get('baidu_nmt_app_id', '').strip())
        self.baidu_nmt_id_edit.textChanged.connect(lambda v: self.settings.set('baidu_nmt_app_id', v.strip()))
        baidu_nmt_id_row.addWidget(self.baidu_nmt_id_edit, 1)
        baidu_nmt_layout.addLayout(baidu_nmt_id_row)

        baidu_nmt_key_row = QHBoxLayout()
        baidu_nmt_key_row.setSpacing(12)
        baidu_nmt_key_label = QLabel("App Key")
        baidu_nmt_key_label.setStyleSheet("font-size: 13px; color: #495057; font-weight: 500;")
        baidu_nmt_key_label.setFixedWidth(85)
        baidu_nmt_key_row.addWidget(baidu_nmt_key_label)
        self.baidu_nmt_key_edit = QLineEdit()
        self.baidu_nmt_key_edit.setPlaceholderText("输入百度通用 App Key")
        self.baidu_nmt_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.baidu_nmt_key_edit.setText(self.settings.get('baidu_nmt_app_key', '').strip())
        self.baidu_nmt_key_edit.textChanged.connect(lambda v: self.settings.set('baidu_nmt_app_key', v.strip()))
        baidu_nmt_key_row.addWidget(self.baidu_nmt_key_edit, 1)
        baidu_nmt_layout.addLayout(baidu_nmt_key_row)

        config_layout.addWidget(self.baidu_nmt_frame)

        layout.addWidget(config_group)

        layout.addStretch()

        self._update_config_visibility(current_provider)

    def _button_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {darken_color(color)};
            }}
        """

    def _on_provider_changed(self):
        provider = self.provider_combo.currentData()
        self.settings.set('translate_provider', provider)
        self._update_config_visibility(provider)

    def _update_config_visibility(self, provider):
        self.tencent_frame.setVisible(provider == "tencent")
        self.baidu_llm_frame.setVisible(provider == "baidu_llm")
        self.baidu_nmt_frame.setVisible(provider == "baidu_nmt")

    def load_ocr(self):
        if self.ocr_service.is_loaded():
            self.translate_btn.setEnabled(True)
            self.translate_btn.setText("截图翻译")
            return
        self.translate_btn.setEnabled(False)
        self.translate_btn.setText("加载OCR...")
        self._ocr_load_timer.start(300)

    def _do_load_ocr(self):
        self.ocr_service.load_async(callback=self._ocr_loaded_signal.emit)

    def _on_ocr_loaded(self, success):
        if success:
            self.translate_btn.setEnabled(True)
            self.translate_btn.setText("截图翻译")
        else:
            self.translate_btn.setEnabled(False)
            self.translate_btn.setText("OCR不可用")

    def release_ocr(self):
        self._ocr_load_timer.stop()
        self.ocr_service.release()
        self.translate_btn.setEnabled(False)
        self.translate_btn.setText("截图翻译")

    def _capture_region(self):
        if not HAS_MSS or not HAS_PIL:
            return None

        self.selector = RegionSelector()
        self.selector.setup_fullscreen()

        while self.selector.isVisible():
            QApplication.processEvents()

        if self.selector.selected_rect is None or self.selector.selected_rect.width() < 10:
            return None

        rect = self.selector.selected_rect
        self.last_screenshot_rect = rect

        with mss.mss() as sct:
            monitor = {
                "top": rect.y(),
                "left": rect.x(),
                "width": rect.width(),
                "height": rect.height()
            }
            screenshot = sct.grab(monitor)
            return Image.frombytes("RGB", screenshot.size, screenshot.rgb), rect

    def _build_bbox_items(self, text_blocks, screenshot_rect, status_text=None):
        items = []
        for block in text_blocks:
            bbox_abs = QRect(
                block.bbox[0] + screenshot_rect.x(),
                block.bbox[1] + screenshot_rect.y(),
                block.bbox[2],
                block.bbox[3]
            )
            if status_text:
                items.append((bbox_abs, block.text, status_text))
            else:
                items.append((bbox_abs, block.text))
        return items

    def _start_translation_thread(self, text_blocks, screenshot_rect):
        if self.translation_thread and self.translation_thread.isRunning():
            self.translation_thread.cancel()
            self.translation_thread.quit()
            self.translation_thread.wait(1000)

        self.translation_thread = TranslationThread(
            text_blocks, self.translation_service, screenshot_rect
        )
        self.translation_thread.progress_signal.connect(self._on_translation_progress)
        self.translation_thread.finished_signal.connect(self._on_translation_finished)
        self.translation_thread.error_signal.connect(self._on_translation_error)
        self.translation_thread.start()

    def _start_translate(self):
        if not HAS_MSS or not HAS_PIL:
            QMessageBox.warning(self, "提示", "缺少 Pillow 或 mss 库，无法截图")
            return

        provider = self.provider_combo.currentData()
        if provider == "baidu_llm":
            if not self.settings.get('baidu_llm_app_id', '').strip() or not self.settings.get('baidu_llm_app_key', '').strip():
                QMessageBox.warning(self, "翻译未配置", "请先在下方「API 密钥配置」中填写百度大模型 App ID 和 App Key")
                return
        elif provider == "baidu_nmt":
            if not self.settings.get('baidu_nmt_app_id', '').strip() or not self.settings.get('baidu_nmt_app_key', '').strip():
                QMessageBox.warning(self, "翻译未配置", "请先在下方「API 密钥配置」中填写百度通用 App ID 和 App Key")
                return
        elif provider == "tencent":
            if not self.settings.get('tencent_secret_id', '').strip() or not self.settings.get('tencent_secret_key', '').strip():
                QMessageBox.warning(self, "翻译未配置", "请先在下方「API 密钥配置」中填写腾讯云 Secret ID 和 Secret Key")
                return

        result = self._capture_region()
        if result is None:
            return

        image, screenshot_rect = result

        if not self.ocr_service.is_available():
            err = self.ocr_service.get_init_error() or "OCR 引擎不可用（PaddleOCR 未正确打包）"
            _write_error_log(err)
            QMessageBox.critical(self, "OCR 错误", f"OCR 初始化失败：{err}")
            return

        text_blocks = self.ocr_service.recognize(image)
        if not text_blocks:
            QMessageBox.information(self, "提示", "未识别到文字，请重试")
            return

        self.last_text_blocks = text_blocks
        self.last_screenshot_rect = screenshot_rect

        if self.mask_translation_overlay is None:
            self.mask_translation_overlay = MaskTranslationOverlay(self.sticky_manager)
            self.mask_translation_overlay.rect_changed.connect(self._on_rect_changed)

        initial_items = self._build_bbox_items(text_blocks, screenshot_rect, "翻译中...")
        self.mask_translation_overlay.set_texts(initial_items, screenshot_rect)
        self.mask_translation_overlay.show()
        self._start_translation_thread(text_blocks, screenshot_rect)

    def _on_translation_progress(self, index, original, translated):
        if self.mask_translation_overlay and self.mask_translation_overlay.text_items:
            if index < len(self.mask_translation_overlay.text_items):
                self.mask_translation_overlay.text_items[index] = (
                    self.mask_translation_overlay.text_items[index][0],
                    original,
                    translated
                )
                self.mask_translation_overlay.all_translated_text = "\n".join(
                    [item[2] for item in self.mask_translation_overlay.text_items]
                )
                self.mask_translation_overlay.update()

    def _on_translation_finished(self, overlay_items):
        if self.mask_translation_overlay:
            self.mask_translation_overlay.set_texts(overlay_items, self.last_screenshot_rect)

    def _on_translation_error(self, msg):
        _write_error_log(msg)
        QMessageBox.warning(self, "翻译提示", f"{msg}\n请检查 API 密钥配置和网络连接")

    def _on_rect_changed(self, new_rect):
        if not HAS_MSS or not HAS_PIL:
            return

        with mss.mss() as sct:
            monitor = {
                "top": new_rect.y(),
                "left": new_rect.x(),
                "width": new_rect.width(),
                "height": new_rect.height()
            }
            screenshot = sct.grab(monitor)
            image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

        if not self.ocr_service.is_available():
            return

        text_blocks = self.ocr_service.recognize(image)
        if not text_blocks:
            return

        self.last_text_blocks = text_blocks
        self.last_screenshot_rect = new_rect

        initial_items = self._build_bbox_items(text_blocks, new_rect, "翻译中...")
        self.mask_translation_overlay.set_texts(initial_items, new_rect)
        self._start_translation_thread(text_blocks, new_rect)

    def clear_overlays(self):
        if self.translation_thread and self.translation_thread.isRunning():
            self.translation_thread.cancel()
            self.translation_thread.quit()
            self.translation_thread.wait(1000)

        if self.translation_overlay:
            self.translation_overlay.clear()
        if self.mask_translation_overlay:
            self.mask_translation_overlay.clear()

    def closeEvent(self, event):
        if self.translation_thread and self.translation_thread.isRunning():
            self.translation_thread.cancel()
            self.translation_thread.quit()
            self.translation_thread.wait(2000)
        if self.translation_overlay:
            self.translation_overlay.close()
        if self.mask_translation_overlay:
            self.mask_translation_overlay.close()
        super().closeEvent(event)
