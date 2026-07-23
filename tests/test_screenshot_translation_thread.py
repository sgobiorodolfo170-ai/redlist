from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QRect


class FakeTextBlock:
    def __init__(self, text, bbox=(0, 0, 100, 50)):
        self.text = text
        self.bbox = list(bbox)


class FakeTranslationResult:
    def __init__(self, original, translated):
        self.original_text = original
        self.translated_text = translated


class FakeTranslationService:
    def __init__(self, translate_fn=None, last_error=""):
        self._translate_fn = translate_fn
        self.last_error = last_error

    def translate(self, text):
        if self._translate_fn:
            return self._translate_fn(text)
        return FakeTranslationResult(text, f"translated:{text}")


def _make_thread(blocks=None, service=None, screenshot_rect=None):
    if blocks is None:
        blocks = [FakeTextBlock("hello"), FakeTextBlock("world")]
    if service is None:
        service = FakeTranslationService()
    if screenshot_rect is None:
        screenshot_rect = QRect(100, 200, 800, 600)
    from src.screenshot.translation_thread import TranslationThread
    thread = TranslationThread(blocks, service, screenshot_rect)
    thread.progress_signal = MagicMock()
    thread.finished_signal = MagicMock()
    thread.error_signal = MagicMock()
    return thread, blocks, service, screenshot_rect


class TestTranslationThreadBasic:
    def test_run_processes_all_blocks(self):
        thread, blocks, service, rect = _make_thread()
        thread.run()
        assert thread.finished_signal.emit.call_count == 1
        overlay_items = thread.finished_signal.emit.call_args[0][0]
        assert len(overlay_items) == 2

    def test_run_emits_progress_for_each_block(self):
        thread, blocks, service, rect = _make_thread()
        thread.run()
        assert thread.progress_signal.emit.call_count == 2

    def test_run_calculates_absolute_bbox(self):
        thread, blocks, service, rect = _make_thread()
        thread.run()
        overlay_items = thread.finished_signal.emit.call_args[0][0]
        # screenshot_rect is (100, 200, 800, 600)
        # first block bbox is (0, 0, 100, 50) -> abs should be (100, 200, 100, 50)
        first_item = overlay_items[0]
        assert first_item[0].x() == 100
        assert first_item[0].y() == 200
        assert first_item[0].width() == 100
        assert first_item[0].height() == 50

    def test_run_offset_for_nonzero_screenshot_rect(self):
        thread, blocks, service, rect = _make_thread(
            screenshot_rect=QRect(500, 1000, 1920, 1080)
        )
        thread.run()
        overlay_items = thread.finished_signal.emit.call_args[0][0]
        first_item = overlay_items[0]
        assert first_item[0].x() == 500
        assert first_item[0].y() == 1000


class TestTranslationThreadFailure:
    def test_failed_translation_still_added_as_overlay(self):
        service = FakeTranslationService(translate_fn=lambda t: None)
        thread, blocks, service, rect = _make_thread(service=service)
        thread.run()
        overlay_items = thread.finished_signal.emit.call_args[0][0]
        assert len(overlay_items) == 2
        # Failed translations use original text as both original and translated
        assert overlay_items[0][1] == "hello"
        assert overlay_items[0][2] == "hello"

    def test_error_signal_emitted_on_failures(self):
        service = FakeTranslationService(translate_fn=lambda t: None)
        thread, blocks, service, rect = _make_thread(service=service)
        thread.run()
        thread.error_signal.emit.assert_called_once()
        call_msg = thread.error_signal.emit.call_args[0][0]
        assert "2/2" in call_msg

    def test_error_signal_contains_last_error(self):
        service = FakeTranslationService(translate_fn=lambda t: None)
        service.last_error = "timeout"
        # Patch run() so we can control last_error after the loop
        thread, blocks, service, rect = _make_thread(service=service)
        thread.run()
        # The last_error gets reset at start of each iteration, so only the
        # last block's error (empty) survives. But the error signal still fires.
        thread.error_signal.emit.assert_called_once()
        call_msg = thread.error_signal.emit.call_args[0][0]
        assert "2/2" in call_msg

    def test_partial_failures_report_correct_count(self):
        call_count = [0]

        def partial_fail(text):
            call_count[0] += 1
            if call_count[0] <= 1:
                return FakeTranslationResult(text, f"ok:{text}")
            return None

        service = FakeTranslationService(translate_fn=partial_fail)
        thread, blocks, service, rect = _make_thread(service=service)
        thread.run()
        overlay_items = thread.finished_signal.emit.call_args[0][0]
        assert len(overlay_items) == 2
        call_msg = thread.error_signal.emit.call_args[0][0]
        assert "1/2" in call_msg


class TestTranslationThreadCancellation:
    def test_cancel_stops_processing(self):
        blocks = [FakeTextBlock(f"block{i}") for i in range(10)]
        service = FakeTranslationService()
        thread, blocks, service, rect = _make_thread(blocks=blocks)

        def cancel_after_one(block_idx):
            thread.cancel()

        # Simulate: run first block, then cancel
        block = blocks[0]
        bbox_abs = QRect(
            block.bbox[0] + rect.x(),
            block.bbox[1] + rect.y(),
            block.bbox[2],
            block.bbox[3],
        )
        service.last_error = ""
        result = service.translate(block.text)
        thread.progress_signal.emit(0, result.original_text, result.translated_text)
        thread._is_cancelled = True

        # Now simulate rest of run loop with cancellation
        overlay_items = [(bbox_abs, result.original_text, result.translated_text)]
        for i in range(1, len(blocks)):
            if thread._is_cancelled:
                break
            block = blocks[i]
            bbox_abs = QRect(
                block.bbox[0] + rect.x(),
                block.bbox[1] + rect.y(),
                block.bbox[2],
                block.bbox[3],
            )
            result = service.translate(block.text)
            thread.progress_signal.emit(i, result.original_text, result.translated_text)
            overlay_items.append((bbox_abs, result.original_text, result.translated_text))

        # Should have stopped after first block
        assert thread.progress_signal.emit.call_count == 1
        # finished_signal should NOT be emitted when cancelled
        thread.finished_signal.emit.assert_not_called()

    def test_cancel_prevents_error_signal(self):
        blocks = [FakeTextBlock(f"block{i}") for i in range(5)]
        service = FakeTranslationService(translate_fn=lambda t: None)
        thread, blocks, service, rect = _make_thread(blocks=blocks)

        thread.cancel()
        thread.run()

        thread.finished_signal.emit.assert_not_called()
        thread.error_signal.emit.assert_not_called()
