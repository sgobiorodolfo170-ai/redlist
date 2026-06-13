import gc
import hashlib
import os
import sys
import threading
from dataclasses import dataclass
from typing import List, Optional, Tuple

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None

from src.utils.cache import get_cache
from src.utils.logger import get_logger

logger = get_logger("OCR")


@dataclass
class TextBlock:
    text: str
    bbox: Tuple[int, int, int, int]
    confidence: float

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "bbox": self.bbox,
            "confidence": self.confidence
        }


class OCRService:
    CACHE_NAME = "ocr_cache"
    CACHE_MAX_SIZE = 200
    CACHE_TTL = 1800
    _instance_lock = threading.Lock()
    _instance = None

    def __new__(cls, use_gpu: bool = False):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, use_gpu: bool = False):
        if self._initialized:
            return

        self.use_gpu = use_gpu
        self._ocr = None
        self.available = HAS_PIL and HAS_NUMPY
        self._init_error = None
        self._loading = False
        self._cancel_load = False
        self._init_lock = threading.Lock()
        self._initialized = True

    def load_async(self, callback=None):
        with self._init_lock:
            if self._loading:
                logger.debug("[OCR] Already loading, ignoring duplicate request")
                return
            if self._ocr is not None:
                logger.debug("[OCR] Already loaded")
                if callback:
                    callback(True)
                return
            if not self.available:
                logger.warning(f"[OCR] Not available: PIL={HAS_PIL}, NUMPY={HAS_NUMPY}")
                if callback:
                    callback(False)
                return
            self._loading = True
            self._cancel_load = False

        def _load():
            try:
                logger.info("[OCR] Loading PaddleOCR in background...")
                from paddleocr import PaddleOCR

                ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                    use_gpu=self.use_gpu,
                    show_log=False
                )

                with self._init_lock:
                    if self._cancel_load:
                        logger.info("[OCR] Load cancelled, discarding instance")
                        self._loading = False
                        if callback:
                            callback(False)
                        return
                    self._ocr = ocr
                    self._loading = False
                    self.available = True
                    self._init_error = None

                logger.info("[OCR] PaddleOCR loaded successfully")
                if callback:
                    callback(True)
            except ImportError as e:
                with self._init_lock:
                    self._loading = False
                    self.available = False
                    self._init_error = f"ImportError: {e}"
                logger.error(f"[OCR] ImportError: {e}")
                if callback:
                    callback(False)
            except Exception as e:
                with self._init_lock:
                    self._loading = False
                    self.available = False
                    self._init_error = str(e)
                logger.exception(f"[OCR] Load failed: {e}")
                if callback:
                    callback(False)

        thread = threading.Thread(target=_load, daemon=True)
        thread.start()

    def release(self):
        with self._init_lock:
            self._cancel_load = True

            if self._ocr is not None:
                logger.info("[OCR] Releasing OCR memory...")
                for name in ('text_detector', 'text_recognizer', 'text_classifier'):
                    comp = getattr(self._ocr, name, None)
                    if comp and hasattr(comp, 'predictor'):
                        try:
                            comp.predictor.clear_intermediate_tensor()
                            comp.predictor.try_shrink_memory()
                        except Exception:
                            pass
                self._ocr = None
                self._loading = False
                logger.info("[OCR] OCR instance released")

        collected = gc.collect()
        logger.debug(f"[OCR] GC collected {collected} objects")

    def is_loading(self) -> bool:
        return self._loading

    def is_loaded(self) -> bool:
        return self._ocr is not None

    def get_init_error(self) -> Optional[str]:
        return self._init_error

    def is_available(self) -> bool:
        return self.available

    def _compute_image_hash(self, image) -> str:
        if isinstance(image, str):
            try:
                with open(image, 'rb') as f:
                    return hashlib.md5(f.read()).hexdigest()
            except Exception:
                return hashlib.md5(str(image).encode()).hexdigest()
        elif isinstance(image, np.ndarray):
            return hashlib.md5(image.tobytes()).hexdigest()
        elif hasattr(image, 'tobytes'):
            return hashlib.md5(image.tobytes()).hexdigest()
        else:
            return hashlib.md5(str(image).encode()).hexdigest()

    def recognize(self, image) -> List[TextBlock]:
        if not self.available or self._ocr is None:
            return []

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
            result = self._ocr.ocr(input_data, cls=True)
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
                    bbox = (int(min(x_coords)), int(min(y_coords)),
                           int(max(x_coords)), int(max(y_coords)))

                    if confidence < 0.5:
                        continue

                    text_blocks.append(TextBlock(
                        text=text,
                        bbox=bbox,
                        confidence=confidence
                    ))

        text_blocks.sort(key=lambda b: b.bbox[1])

        if text_blocks:
            cache.set(image_hash, text_blocks)
            logger.debug(f"[OCR] Cached result for image hash: {image_hash[:8]}...")

        return text_blocks

    def clear_cache(self) -> None:
        cache = get_cache(self.CACHE_NAME, self.CACHE_MAX_SIZE, self.CACHE_TTL)
        cache.clear()
        logger.info("[OCR] Cache cleared")

    @classmethod
    def get_instance(cls, use_gpu: bool = False) -> 'OCRService':
        return cls(use_gpu)
