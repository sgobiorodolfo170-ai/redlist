import threading
from functools import wraps
from typing import Callable, Optional


class Debouncer:
    def __init__(self, delay_ms: int = 500):
        self.delay_ms = delay_ms
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._pending_func: Optional[Callable] = None
        self._pending_args: tuple = ()
        self._pending_kwargs: dict = {}

    def call(self, func: Callable, *args, **kwargs) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()

            self._pending_func = func
            self._pending_args = args
            self._pending_kwargs = kwargs

            self._timer = threading.Timer(
                self.delay_ms / 1000.0,
                self._execute
            )
            self._timer.daemon = True
            self._timer.start()

    def _execute(self) -> None:
        with self._lock:
            if self._pending_func is not None:
                try:
                    self._pending_func(*self._pending_args, **self._pending_kwargs)
                except Exception:
                    pass
                finally:
                    self._pending_func = None
                    self._pending_args = ()
                    self._pending_kwargs = {}

    def cancel(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None

    def flush(self) -> None:
        self.cancel()
        self._execute()


def debounce(delay_ms: int = 500):
    debouncer = Debouncer(delay_ms)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            debouncer.call(func, *args, **kwargs)

        wrapper.cancel = debouncer.cancel
        wrapper.flush = debouncer.flush
        return wrapper

    return decorator
