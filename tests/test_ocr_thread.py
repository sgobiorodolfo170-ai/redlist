from unittest.mock import MagicMock, patch

import pytest

from src.ocr.ocr_service import OCRService, TextBlock
from src.ocr.ocr_thread import OCRThread


class FakeImage:
    def tobytes(self):
        return b"fake_image_data"


@pytest.fixture(autouse=True)
def reset_singleton():
    OCRService._instance = None
    yield
    OCRService._instance = None


class TestOCRThread:
    def _make_mock_service(self, ocr_result=None):
        svc = MagicMock(spec=[
            'recognize', 'is_available', 'is_loaded',
            'release', 'load_async', 'get_init_error'
        ])
        svc.is_available.return_value = True
        if ocr_result is not None:
            svc.recognize.return_value = ocr_result
        return svc

    def test_initial_state(self):
        with patch("src.ocr.ocr_thread.OCRService") as mock_cls:
            mock_cls.return_value = self._make_mock_service()
            thread = OCRThread(FakeImage())
            assert thread.image is not None

    def test_recognize_emits_result(self):
        with patch("src.ocr.ocr_thread.OCRService") as mock_cls:
            mock_cls.return_value = self._make_mock_service(
                ocr_result=[TextBlock("hello", (0, 0, 10, 10), 0.95)]
            )
            results = []
            thread = OCRThread(FakeImage())
            thread.finished_signal.connect(lambda r: results.append(r))
            thread.run()

        assert len(results) == 1
        assert results[0][0].text == "hello"

    def test_recognize_emits_empty_on_no_results(self):
        with patch("src.ocr.ocr_thread.OCRService") as mock_cls:
            mock_cls.return_value = self._make_mock_service(ocr_result=[])
            results = []
            thread = OCRThread(FakeImage())
            thread.finished_signal.connect(lambda r: results.append(r))
            thread.run()

        assert len(results) == 1
        assert results[0] == []

    def test_cancel_before_run(self):
        with patch("src.ocr.ocr_thread.OCRService") as mock_cls:
            mock_cls.return_value = self._make_mock_service()
            thread = OCRThread(FakeImage())
            thread.cancel()
            thread.run()
            assert thread._result == []

    def test_not_available_emits_error(self):
        with patch("src.ocr.ocr_thread.OCRService") as mock_cls:
            svc = self._make_mock_service()
            svc.is_available.return_value = False
            mock_cls.return_value = svc

            errors = []
            thread = OCRThread(FakeImage())
            thread.error_signal.connect(lambda e: errors.append(e))
            thread.run()

        assert len(errors) == 1

    def test_recognize_exception_emits_error(self):
        with patch("src.ocr.ocr_thread.OCRService") as mock_cls:
            svc = self._make_mock_service()
            svc.recognize.side_effect = RuntimeError("recognize failed")
            mock_cls.return_value = svc

            errors = []
            thread = OCRThread(FakeImage())
            thread.error_signal.connect(lambda e: errors.append(e))
            thread.run()

        assert len(errors) == 1
