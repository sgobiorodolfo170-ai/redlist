from PyQt6.QtCore import QRect, QThread, pyqtSignal

from src.utils.logger import get_logger

logger = get_logger("ScreenshotTranslate")


class TranslationThread(QThread):
    progress_signal = pyqtSignal(int, str, str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, text_blocks, translation_service, screenshot_rect):
        super().__init__()
        self.text_blocks = text_blocks
        self.translation_service = translation_service
        self.screenshot_rect = screenshot_rect
        self._is_cancelled = False
        self._error_count = 0
        self._total_count = len(text_blocks)

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        overlay_items = []
        failed_count = 0
        for i, block in enumerate(self.text_blocks):
            if self._is_cancelled:
                break

            bbox_abs = QRect(
                block.bbox[0] + self.screenshot_rect.x(),
                block.bbox[1] + self.screenshot_rect.y(),
                block.bbox[2],
                block.bbox[3]
            )

            self.translation_service.last_error = ""
            result = self.translation_service.translate(block.text)
            if result:
                overlay_items.append((bbox_abs, result.original_text, result.translated_text))
                self.progress_signal.emit(i, result.original_text, result.translated_text)
            else:
                overlay_items.append((bbox_abs, block.text, block.text))
                self.progress_signal.emit(i, block.text, block.text)
                failed_count += 1

        if not self._is_cancelled:
            self.finished_signal.emit(overlay_items)
            if failed_count > 0:
                err_detail = self.translation_service.last_error or "未知错误"
                self.error_signal.emit(
                    f"翻译失败：{failed_count}/{self._total_count} 个文本块未成功翻译\n原因：{err_detail}"
                )
