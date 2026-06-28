import threading
from unittest.mock import MagicMock, patch

import pytest

from src.ocr.ocr_service import OCRService, TextBlock


@pytest.fixture(autouse=True)
def reset_singleton():
    OCRService._instance = None
    yield
    OCRService._instance = None


def make_fresh_svc():
    svc = OCRService.__new__(OCRService)
    svc._lock = threading.Lock()
    svc.use_gpu = False
    svc._ocr = MagicMock()
    svc._loading = False
    svc._cancel_load = False
    svc._pending_callback = None
    svc._initialized = True
    return svc


class TestTextBlock:
    def test_fields(self):
        tb = TextBlock(text="hello", bbox=(0, 0, 10, 20), confidence=0.95)
        assert tb.text == "hello"
        assert tb.bbox == (0, 0, 10, 20)
        assert tb.confidence == 0.95


class TestOCRServiceSingleton:
    def test_singleton_returns_same_instance(self, reset_singleton):
        a = OCRService()
        b = OCRService()
        assert a is b

    def test_singleton_different_use_gpu_params(self, reset_singleton):
        a = OCRService(use_gpu=True)
        b = OCRService(use_gpu=False)
        assert a is b

    def test_concurrent_singleton_access(self, reset_singleton):
        instances = []

        def get_instance():
            instances.append(OCRService())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(instances) == 10
        assert all(i is instances[0] for i in instances)


class TestOCRServiceLoadAsync:
    def test_load_async_twice_stores_latest_callback(self, reset_singleton):
        svc = make_fresh_svc()
        svc._ocr = None
        svc._loading = False

        cb1 = MagicMock()
        cb2 = MagicMock()

        with patch("paddleocr.PaddleOCR", side_effect=ImportError("no paddle")):
            svc._loading = True
            svc.load_async(callback=cb1)
            assert svc._pending_callback is cb1

            svc.load_async(callback=cb2)
            assert svc._pending_callback is cb2

    def test_release_clears_pending(self, reset_singleton):
        svc = make_fresh_svc()
        svc._pending_callback = MagicMock()

        svc.release()
        assert svc._pending_callback is None

    def test_release_with_loaded_ocr(self, reset_singleton):
        svc = make_fresh_svc()
        mock_predictor = MagicMock()
        svc._ocr.text_detector.predictor = mock_predictor

        svc.release()
        assert svc._ocr is None
        mock_predictor.clear_intermediate_tensor.assert_called_once()

    def test_release_cancels_loading(self, reset_singleton):
        svc = make_fresh_svc()
        svc._loading = True
        svc.release()
        assert svc._cancel_load


class TestOCRServiceRecognize:
    def test_returns_empty_when_not_loaded(self, reset_singleton):
        svc = make_fresh_svc()
        svc._ocr = None
        result = svc.recognize("dummy.png")
        assert result == []

    @patch("src.ocr.ocr_service.get_cache")
    def test_cache_used_for_same_image(self, mock_get_cache, reset_singleton):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mock_get_cache.return_value = mock_cache

        svc = make_fresh_svc()
        svc._ocr.ocr.return_value = [[
            [[[0, 0], [10, 0], [10, 10], [0, 10]], ("hello", 0.95)]
        ]]

        r1 = svc.recognize("test.png")
        assert len(r1) == 1
        assert r1[0].text == "hello"
        mock_cache.set.assert_called_once()

    @patch("src.ocr.ocr_service.get_cache")
    def test_cache_hit_returns_directly(self, mock_get_cache, reset_singleton):
        cached = [TextBlock("cached", (0, 0, 1, 1), 0.99)]
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached
        mock_get_cache.return_value = mock_cache

        svc = make_fresh_svc()

        result = svc.recognize("test.png")
        assert result is cached
        svc._ocr.ocr.assert_not_called()

    @patch("src.ocr.ocr_service.get_cache")
    def test_low_confidence_filtered(self, mock_get_cache, reset_singleton):
        mock_get_cache.return_value = MagicMock()
        mock_get_cache.return_value.get.return_value = None

        svc = make_fresh_svc()
        svc._ocr.ocr.return_value = [[
            [[[0, 0], [10, 0], [10, 10], [0, 10]], ("keep", 0.95)],
            [[[20, 0], [30, 0], [30, 10], [20, 10]], ("drop", 0.3)],
        ]]

        result = svc.recognize("test.png")
        assert len(result) == 1
        assert result[0].text == "keep"

    @patch("src.ocr.ocr_service.get_cache")
    def test_text_blocks_sorted_by_y(self, mock_get_cache, reset_singleton):
        mock_get_cache.return_value = MagicMock()
        mock_get_cache.return_value.get.return_value = None

        svc = make_fresh_svc()
        svc._ocr.ocr.return_value = [[
            [[[0, 100], [10, 100], [10, 110], [0, 110]], ("second", 0.9)],
            [[[0, 0], [10, 0], [10, 10], [0, 10]], ("first", 0.9)],
        ]]

        result = svc.recognize("test.png")
        assert len(result) == 2
        assert result[0].text == "first"
        assert result[1].text == "second"

    @patch("src.ocr.ocr_service.get_cache")
    def test_ocr_error_returns_empty(self, mock_get_cache, reset_singleton):
        mock_get_cache.return_value = MagicMock()
        mock_get_cache.return_value.get.return_value = None

        svc = make_fresh_svc()
        svc._ocr.ocr.side_effect = RuntimeError("ocr failed")

        result = svc.recognize("test.png")
        assert result == []


class TestOCRServiceLifecycle:
    def test_is_loaded(self, reset_singleton):
        svc = make_fresh_svc()
        svc._ocr = None
        assert not svc.is_loaded()

        svc._ocr = MagicMock()
        assert svc.is_loaded()

    def test_is_available(self, reset_singleton):
        svc = make_fresh_svc()
        svc._ocr = None
        assert not svc.is_available()

        svc._ocr = MagicMock()
        assert svc.is_available()
