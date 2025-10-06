from datetime import timedelta

from core.storage.kv_storage import KVStorage
from core.utils.lru.lru_cache import TLRUCache


class LocalKVStorage(KVStorage):
    def __init__(self):
        self._cache = TLRUCache(capacity=1000, ttl=lambda _, __: None)

    async def setex(self, key: str, expiration: timedelta, value: bytes | str) -> None:
        self._cache.setex(key, expiration, value)

    async def set(self, key: str, value: bytes | str) -> None:
        self._cache.set(key, value)

    async def get(self, key: str) -> bytes | None:
        try:
            return self._cache.get(key)
        except KeyError:
            return None

    async def close(self) -> None:
        pass
