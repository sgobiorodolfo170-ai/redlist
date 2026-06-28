from PyQt6.QtCore import QThread, pyqtSignal

from src.ocr.ocr_service import OCRService
from src.utils.logger import get_logger

logger = get_logger("OCRThread")


class OCRThread(QThread):
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = image
        self._is_cancelled = False
        self._ocr_service = OCRService()
        self._result = []

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        if not self._ocr_service.is_available():
            self.error_signal.emit("OCR 引擎不可用")
            return

        try:
            text_blocks = self._ocr_service.recognize(self.image)
            if self._is_cancelled:
                return
            self._result = text_blocks
            self.finished_signal.emit(text_blocks)
        except Exception as e:
            logger.exception(f"[OCRThread] Recognize failed: {e}")
            if not self._is_cancelled:
                self.error_signal.emit(str(e))
