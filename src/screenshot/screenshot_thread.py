from PyQt6.QtCore import QThread, pyqtSignal

from src.utils.logger import get_logger

logger = get_logger("ScreenshotThread")


class ScreenshotCaptureThread(QThread):
    finished_signal = pyqtSignal(object)

    def __init__(self, monitor_dict, parent=None):
        super().__init__(parent)
        self.monitor = monitor_dict
        self._cancelled = False

    def run(self):
        try:
            import mss
            from PIL import Image

            with mss.mss() as sct:
                if self._cancelled:
                    return
                screenshot = sct.grab(self.monitor)
                if self._cancelled:
                    return
                image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                if not self._cancelled:
                    self.finished_signal.emit(image)
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")

    def cancel(self):
        self._cancelled = True
