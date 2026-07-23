import gc
import hashlib
import os
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    import numpy as np
except ImportError:
    np = None

from src.utils.cache import get_cache
from src.utils.logger import get_logger

logger = get_logger("OCR")


@dataclass
class TextBlock:
    text: str
    bbox: tuple[int, int, int, int]
    confidence: float


class OCRService:
    CACHE_NAME = "ocr_cache"
    CACHE_MAX_SIZE = 200
    CACHE_TTL = 1800
    _instance_lock = threading.Lock()
    _instance = None
    _lock: threading.Lock
    use_gpu: bool
    _ocr: Optional[object]
    _loading: bool
    _cancel_load: bool
    _pending_callback: Optional[Callable]
    _initialized: bool
    _init_error: Optional[str]

    def __new__(cls, use_gpu: bool = False):
        with cls._instance_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._lock = threading.Lock()
                inst.use_gpu = use_gpu
                inst._ocr = None
                inst._loading = False
                inst._cancel_load = False
                inst._pending_callback = None
                inst._initialized = True
                inst._init_error = None
                cls._instance = inst
            return cls._instance

    def __init__(self, use_gpu: bool = False):
        pass

    def load_async(self, callback: Optional[Callable] = None):
        with self._lock:
            self._init_error = None
            if self._loading:
                self._pending_callback = callback
                logger.debug("[OCR] Already loading, will notify latest caller")
                return
            if self._ocr is not None:
                logger.debug("[OCR] Already loaded")
                if callback:
                    callback(True)
                return
            self._loading = True
            self._cancel_load = False
            self._pending_callback = callback

        def _load():
            try:
                logger.info("[OCR] Loading PaddleOCR in background...")
                from paddleocr import PaddleOCR

                ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=self.use_gpu, show_log=False)

                with self._lock:
                    if self._cancel_load:
                        logger.info("[OCR] Load cancelled, discarding instance")
                        self._loading = False
                        cb = self._pending_callback
                        self._pending_callback = None
                        if cb:
                            cb(False)
                        return
                    self._ocr = ocr
                    self._loading = False
                    cb = self._pending_callback
                    self._pending_callback = None

                logger.info("[OCR] PaddleOCR loaded successfully")
                if cb:
                    cb(True)
            except ImportError as e:
                err_msg = f"PaddleOCR 导入失败：{e}"
                with self._lock:
                    self._loading = False
                    self._init_error = err_msg
                    cb = self._pending_callback
                    self._pending_callback = None
                logger.error(f"[OCR] {err_msg}")
                if cb:
                    cb(False)
            except Exception as e:
                err_msg = f"PaddleOCR 加载失败：{e}"
                with self._lock:
                    self._loading = False
                    self._init_error = err_msg
                    cb = self._pending_callback
                    self._pending_callback = None
                logger.exception(f"[OCR] {err_msg}")
                if cb:
                    cb(False)

        thread = threading.Thread(target=_load, daemon=True)
        thread.start()

    def release(self):
        with self._lock:
            self._cancel_load = True
            self._init_error = None
            if self._ocr is not None:
                logger.info("[OCR] Releasing OCR memory...")
                for name in ("text_detector", "text_recognizer", "text_classifier"):
                    comp = getattr(self._ocr, name, None)
                    if comp and hasattr(comp, "predictor"):
                        try:
                            comp.predictor.clear_intermediate_tensor()
                            comp.predictor.try_shrink_memory()
                        except Exception:
                            pass
                self._ocr = None
                self._loading = False
                self._pending_callback = None
                logger.info("[OCR] OCR instance released")

        collected = gc.collect()
        logger.debug(f"[OCR] GC collected {collected} objects")

    def is_loaded(self) -> bool:
        with self._lock:
            return self._ocr is not None

    def get_init_error(self) -> Optional[str]:
        with self._lock:
            return self._init_error

    def is_available(self) -> bool:
        with self._lock:
            return self._ocr is not None

    def _compute_image_hash(self, image) -> str:
        if isinstance(image, str):
            try:
                with open(image, "rb") as f:
                    return hashlib.md5(f.read()).hexdigest()
            except Exception:
                return hashlib.md5(str(image).encode()).hexdigest()
        try:
            data = image.tobytes() if hasattr(image, "tobytes") else str(image).encode()
            return hashlib.md5(data).hexdigest()
        except Exception:
            return hashlib.md5(str(image).encode()).hexdigest()

    def recognize(self, image) -> List[TextBlock]:
        with self._lock:
            if self._ocr is None:
                return []
            ocr = self._ocr

        image_hash = self._compute_image_hash(image)
        cache = get_cache(self.CACHE_NAME, self.CACHE_MAX_SIZE, self.CACHE_TTL)

        cached_result = cache.get(image_hash)
        if cached_result is not None:
            logger.debug(f"[OCR] Cache hit for image hash: {image_hash[:8]}...")
            return cached_result

        if isinstance(image, str):
            input_data = image
        elif isinstance(image, np.ndarray):
            img_array = image
            if len(img_array.shape) == 2:
                img_array = np.stack([img_array] * 3, axis=-1)
            input_data = img_array
        else:
            img_array = np.array(image)
            if len(img_array.shape) == 2:
                img_array = np.stack([img_array] * 3, axis=-1)
            input_data = img_array

        try:
            result = ocr.ocr(input_data, cls=True)
        except Exception as e:
            logger.error(f"[OCR] 识别失败：{e}")
            return []

        text_blocks = []
        if result and result[0]:
            for line in result[0]:
                if len(line) >= 2:
                    bbox_points = line[0]
                    text, confidence = line[1]

                    x_coords = [p[0] for p in bbox_points]
                    y_coords = [p[1] for p in bbox_points]
                    bbox = (int(min(x_coords)), int(min(y_coords)), int(max(x_coords)), int(max(y_coords)))

                    if confidence < 0.5:
                        continue

                    text_blocks.append(TextBlock(text=text, bbox=bbox, confidence=confidence))

        text_blocks.sort(key=lambda b: b.bbox[1])

        if text_blocks:
            cache.set(image_hash, text_blocks)
            logger.debug(f"[OCR] Cached result for image hash: {image_hash[:8]}...")

        return text_blocks
