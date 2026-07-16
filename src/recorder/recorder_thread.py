import time
from pathlib import Path

from PyQt6.QtCore import QRect, QThread, pyqtSignal

from src.utils.logger import get_logger

logger = get_logger("ScreenRecorder")


class ScreenRecorderThread(QThread):
    frame_captured = pyqtSignal(int, float)
    recording_finished = pyqtSignal(str)
    recording_error = pyqtSignal(str)

    def __init__(self, rect: QRect, output_path: str, fps: int = 20, parent=None):
        super().__init__(parent)
        self.rect = rect
        self.output_path = output_path
        self.fps = fps
        self._running = False

    def run(self):
        self._running = True
        try:
            import cv2
            import mss
            import numpy as np
        except ImportError as e:
            self.recording_error.emit(f"缺少录屏依赖: {e}")
            return

        x, y, w, h = self.rect.x(), self.rect.y(), self.rect.width(), self.rect.height()
        if w < 10 or h < 10:
            self.recording_error.emit("选区太小，无法录制")
            return

        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(self.output_path, fourcc, self.fps, (w, h))
        if not out.isOpened():
            self.recording_error.emit("无法创建视频文件")
            return

        monitor = {"top": y, "left": x, "width": w, "height": h}
        frame_duration = 1.0 / self.fps
        frame_count = 0
        start_time = time.time()

        try:
            with mss.mss() as sct:
                while self._running:
                    loop_start = time.time()

                    img = sct.grab(monitor)
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    out.write(frame)

                    frame_count += 1
                    elapsed = time.time() - start_time
                    self.frame_captured.emit(frame_count, elapsed)

                    sleep_time = frame_duration - (time.time() - loop_start)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
        finally:
            out.release()

        logger.info(f"Recording saved: {self.output_path} ({frame_count} frames)")
        self.recording_finished.emit(self.output_path)

    def stop(self):
        self._running = False
