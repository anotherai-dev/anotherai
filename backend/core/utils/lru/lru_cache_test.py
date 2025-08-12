import time
from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory

from .lru_cache import LRUCache, TLRUCache


class TestLRUCache:
    def test_lru_cache_basic_operations(self):
        cache = LRUCache[int, int](2)

        cache[1] = 1
        cache[2] = 2
        assert cache.peek(1) == 1
        assert cache.peek(2) == 2

        cache[3] = 3
        with pytest.raises(KeyError):
            cache[1]
        assert cache[2] == 2
        assert cache[3] == 3

        cache[4] = 4
        with pytest.raises(KeyError):
            cache[1]
        assert cache[3] == 3
        assert cache[4] == 4

    def test_lru_cache_update_existing_key(self):
        cache = LRUCache[int, int](2)

        cache[1] = 1
        cache[2] = 2
        cache[1] = 10
        assert cache[1] == 10

        assert cache[2] == 2

    def test_lru_cache_capacity(self):
        cache = LRUCache[int, int](1)

        cache[1] = 1
        assert cache[1] == 1

        cache[2] = 2
        with pytest.raises(KeyError):
            cache[1]
        assert cache[2] == 2

    def test_lru_cache_empty(self):
        cache = LRUCache[int, int](2)

        with pytest.raises(KeyError):
            cache[1]


class TestTLRUCache:
    def test_tlru_cache_basic_operations(self):
        cache = TLRUCache[int, int](2, lambda _, __: timedelta(seconds=1))
        cache[1] = 1
        cache[2] = 2

        assert cache[1] == 1
        assert cache[2] == 2

        # Test LRU behavior
        cache[3] = 3
        with pytest.raises(KeyError):
            cache[1]
        assert cache[2] == 2
        assert cache[3] == 3

    def test_tlru_cache_expiration(self, frozen_time: FrozenDateTimeFactory):
        cache = TLRUCache[int, int](2, lambda _, __: timedelta(milliseconds=100))
        cache[1] = 1

        # Value should be available immediately
        assert cache[1] == 1

        # Wait for expiration
        _ = frozen_time.tick(delta=timedelta(milliseconds=200))

        # Value should be expired
        with pytest.raises(KeyError):
            cache[1]

    def test_tlru_cache_different_expiration_times(self, frozen_time: FrozenDateTimeFactory):
        cache = TLRUCache[int, int](3, lambda _, value: timedelta(milliseconds=200 if value % 2 == 0 else 500))
        cache[1] = 1  # odd, expires in 500ms
        cache[2] = 2  # even, expires in 200ms
        cache[3] = 3  # odd, expires in 500ms

        # Wait for even numbers to expire
        frozen_time.tick(delta=timedelta(milliseconds=300))

        # Even number should be expired
        with pytest.raises(KeyError):
            cache[2]

        # Odd numbers should still be available
        assert cache[1] == 1
        assert cache[3] == 3

    def test_tlru_cache_update_extends_time(self, frozen_time: FrozenDateTimeFactory):
        cache = TLRUCache[int, int](2, lambda _, __: timedelta(milliseconds=200))
        cache[1] = 1

        # Wait some time but not enough to expire
        frozen_time.tick(delta=timedelta(milliseconds=100))

        # Update the value
        cache[1] = 1

        # Wait more time (would have expired if not updated)
        time.sleep(0.15)

        # Should still be available because we updated it
        assert cache[1] == 1
