import hashlib
import threading
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Optional


class LRUCache:
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: dict = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None

            if time.time() - self._timestamps.get(key, 0) >= self.ttl_seconds:
                self._remove(key)
                return None

            self._cache.move_to_end(key)
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._remove(key)

            self._cache[key] = value
            self._timestamps[key] = time.time()

            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                self._remove(oldest_key)

    def _remove(self, key: str) -> None:
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


_caches: dict = {}


def get_cache(name: str, max_size: int = 100, ttl_seconds: int = 3600) -> LRUCache:
    if name not in _caches:
        _caches[name] = LRUCache(max_size, ttl_seconds)
    return _caches[name]


def cached(cache_name: str, key_func: Optional[Callable] = None, max_size: int = 100, ttl_seconds: int = 3600):
    cache = get_cache(cache_name, max_size, ttl_seconds)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _make_key(args, kwargs)

            result = cache.get(cache_key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result)

            return result

        wrapper.cache = cache
        wrapper.cache_clear = cache.clear
        return wrapper

    return decorator


def _make_key(args: tuple, kwargs: dict) -> str:
    key_parts = [repr(args)]
    if kwargs:
        key_parts.append(repr(sorted(kwargs.items())))
    key_str = ''.join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()


def image_hash(image_data) -> str:
    if hasattr(image_data, 'tobytes'):
        data = image_data.tobytes()
    elif isinstance(image_data, bytes):
        data = image_data
    else:
        data = str(image_data).encode()

    return hashlib.md5(data).hexdigest()
