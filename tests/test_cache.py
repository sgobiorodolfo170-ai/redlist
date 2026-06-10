from src.utils.cache import LRUCache, cached, get_cache


class TestLRUCache:
    def test_set_and_get(self):
        cache = LRUCache(max_size=10, ttl_seconds=3600)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing(self):
        cache = LRUCache(max_size=10, ttl_seconds=3600)
        assert cache.get("nonexistent") is None

    def test_eviction(self):
        cache = LRUCache(max_size=2, ttl_seconds=3600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_lru_order(self):
        cache = LRUCache(max_size=2, ttl_seconds=3600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.get("a")
        cache.set("c", 3)
        assert cache.get("b") is None
        assert cache.get("a") == 1
        assert cache.get("c") == 3

    def test_ttl_expiry(self):
        cache = LRUCache(max_size=10, ttl_seconds=0)
        cache.set("key", "value")
        assert cache.get("key") is None

    def test_clear(self):
        cache = LRUCache(max_size=10, ttl_seconds=3600)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.size() == 0

    def test_size(self):
        cache = LRUCache(max_size=10, ttl_seconds=3600)
        assert cache.size() == 0
        cache.set("a", 1)
        assert cache.size() == 1


class TestGetCache:
    def test_same_name_returns_same_instance(self):
        c1 = get_cache("shared")
        c2 = get_cache("shared")
        assert c1 is c2

    def test_different_names_different_instances(self):
        c1 = get_cache("alpha")
        c2 = get_cache("beta")
        assert c1 is not c2

    def test_custom_params(self):
        cache = get_cache("custom", max_size=5, ttl_seconds=100)
        assert cache.max_size == 5
        assert cache.ttl_seconds == 100


class TestCachedDecorator:
    def test_cache_hit(self):
        call_count = 0

        @cached("test_hit", max_size=10, ttl_seconds=3600)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert compute(5) == 10
        assert call_count == 1
        assert compute(5) == 10
        assert call_count == 1

    def test_cache_miss_different_args(self):
        call_count = 0

        @cached("test_miss", max_size=10, ttl_seconds=3600)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert compute(5) == 10
        assert call_count == 1
        assert compute(7) == 14
        assert call_count == 2

    def test_cache_clear(self):
        call_count = 0

        @cached("test_clear", max_size=10, ttl_seconds=3600)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        compute(5)
        compute.cache_clear()
        compute(5)
        assert call_count == 2
