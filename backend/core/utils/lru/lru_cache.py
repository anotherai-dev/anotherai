from collections import OrderedDict
from collections.abc import Callable, Hashable
from datetime import UTC, datetime, timedelta
from typing import Any


class LRUCache[K: Hashable, T]:
    def __init__(self, capacity: int):
        self.capacity: int = capacity
        self.cache: OrderedDict[Any, T] = OrderedDict()

    def __getitem__(self, key: K) -> T:
        if key not in self.cache:
            raise KeyError(f"Key {key} not found in cache")

        # Move the key to the end to indicate that it was recently used
        self.cache.move_to_end(key)
        return self.cache[key]

    def __setitem__(self, key: K, value: T) -> None:
        if key in self.cache:
            # Update the value and move the key to the end
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            # Remove the first (least recently used) item
            _ = self.cache.popitem(last=False)

    def __delitem__(self, key: K) -> None:
        del self.cache[key]

    def peek(self, key: K) -> T | None:
        try:
            return self.cache[key]
        except KeyError:
            return None


# We should probably inherit from MutableMapping instead
class TLRUCache[K: Hashable, T]:
    def __init__(self, capacity: int, ttl: Callable[[K, T], timedelta | None]):
        self._cache: LRUCache[K, tuple[datetime | None, T]] = LRUCache[K, tuple[datetime | None, T]](capacity)
        self._ttl: Callable[[K, T], timedelta | None] = ttl

    def __getitem__(self, key: K) -> T:
        val = self._cache[key]
        if val[0] and val[0] < datetime.now(UTC):
            del self._cache[key]
            raise KeyError(f"Key {key} was expired in cache")
        return val[1]

    def __setitem__(self, key: K, value: T) -> None:
        ttl = self._ttl(key, value)
        if ttl:
            self.setex(key, ttl, value)
        else:
            self.set(key, value)

    def get(self, key: K, default: T | None = None) -> T | None:
        try:
            return self[key]
        except KeyError:
            return default

    def setex(self, key: K, expiration: timedelta, value: T) -> None:
        self._cache[key] = (datetime.now(UTC) + expiration, value)

    def set(self, key: K, value: T) -> None:
        self._cache[key] = (None, value)
