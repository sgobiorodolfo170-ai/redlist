from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QRect

from src.ocr.ocr_service import TextBlock
from src.screenshot_translate import TranslationThread


class FakeTranslationResult:
    def __init__(self, original_text, translated_text):
        self.original_text = original_text
        self.translated_text = translated_text


class TestTranslationThread:
    def test_translates_each_block(self):
        service = MagicMock()
        service.translate.side_effect = lambda t: FakeTranslationResult(t, f"{t}-translated")

        blocks = [
            TextBlock(text="hello", bbox=(0, 0, 50, 20), confidence=0.9),
            TextBlock(text="world", bbox=(0, 30, 60, 50), confidence=0.8),
        ]
        rect = QRect(100, 200, 800, 600)

        progress_calls = []
        finished_calls = []

        thread = TranslationThread(blocks, service, rect)
        thread.progress_signal.connect(lambda i, o, t: progress_calls.append((i, o, t)))
        thread.finished_signal.connect(lambda items: finished_calls.append(items))
        thread.run()

        assert service.translate.call_count == 2
        service.translate.assert_any_call("hello")
        service.translate.assert_any_call("world")
        assert len(progress_calls) == 2
        assert progress_calls[0] == (0, "hello", "hello-translated")
        assert progress_calls[1] == (1, "world", "world-translated")
        assert len(finished_calls) == 1
        assert len(finished_calls[0]) == 2

    def test_skips_on_cancellation(self):
        service = MagicMock()
        service.translate.side_effect = lambda t: FakeTranslationResult(t, f"{t}-translated")

        blocks = [
            TextBlock(text="a", bbox=(0, 0, 10, 10), confidence=0.9),
            TextBlock(text="b", bbox=(0, 20, 10, 30), confidence=0.9),
            TextBlock(text="c", bbox=(0, 40, 10, 50), confidence=0.9),
        ]
        rect = QRect(0, 0, 100, 100)

        thread = TranslationThread(blocks, service, rect)
        finished_calls = []
        thread.finished_signal.connect(lambda items: finished_calls.append(items))

        def cancel_after_first(_i, _o, _t):
            thread.cancel()

        thread.progress_signal.connect(cancel_after_first)
        thread.run()

        assert service.translate.call_count >= 1
        assert service.translate.call_count < 3
        assert len(finished_calls) == 0

    def test_preserves_original_on_translate_failure(self):
        service = MagicMock()
        service.translate.return_value = None

        blocks = [
            TextBlock(text="hello", bbox=(0, 0, 50, 20), confidence=0.9),
        ]
        rect = QRect(0, 0, 100, 100)

        progress_calls = []
        finished_calls = []

        thread = TranslationThread(blocks, service, rect)
        thread.progress_signal.connect(lambda i, o, t: progress_calls.append((i, o, t)))
        thread.finished_signal.connect(lambda items: finished_calls.append(items))
        thread.run()

        _, original_text, translated_text = progress_calls[0]
        assert original_text == "hello"
        assert translated_text == "hello"

    def test_computes_absolute_bbox(self):
        service = MagicMock()
        service.translate.return_value = FakeTranslationResult("x", "y")

        blocks = [
            TextBlock(text="hi", bbox=(10, 20, 100, 60), confidence=0.9),
        ]
        rect = QRect(200, 300, 800, 600)

        thread = TranslationThread(blocks, service, rect)
        result_items = []
        thread.finished_signal.connect(lambda items: result_items.extend(items))
        thread.run()

        assert len(result_items) == 1
        bbox_abs, _, _ = result_items[0]
        assert bbox_abs.x() == 210
        assert bbox_abs.y() == 320
        assert bbox_abs.width() == 100
        assert bbox_abs.height() == 60
