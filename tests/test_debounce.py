import time

from src.utils.debounce import Debouncer


class TestDebouncer:
    def test_call_delays_execution(self):
        calls = []

        def fn():
            calls.append(True)

        d = Debouncer(delay_ms=50)
        d.call(fn)
        assert len(calls) == 0
        time.sleep(0.1)
        assert len(calls) == 1

    def test_multiple_calls_debounce(self):
        calls = []

        def fn():
            calls.append(True)

        d = Debouncer(delay_ms=80)
        d.call(fn)
        d.call(fn)
        d.call(fn)
        time.sleep(0.15)
        assert len(calls) == 1

    def test_flush_executes_immediately(self):
        calls = []

        def fn():
            calls.append(True)

        d = Debouncer(delay_ms=5000)
        d.call(fn)
        assert len(calls) == 0
        d.flush()
        assert len(calls) == 1

    def test_cancel_prevents_execution(self):
        calls = []

        def fn():
            calls.append(True)

        d = Debouncer(delay_ms=50)
        d.call(fn)
        d.cancel()
        time.sleep(0.1)
        assert len(calls) == 0
