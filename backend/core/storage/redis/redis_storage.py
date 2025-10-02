from datetime import timedelta
from typing import override

from redis import asyncio as aioredis

from core.storage.kv_storage import KVStorage


class RedisStorage(KVStorage):
    def __init__(self, dsn: str):
        self._client = aioredis.from_url(dsn)

    @override
    async def setex(self, key: str, expiration: timedelta, value: bytes | str) -> None:
        await self._client.setex(key, expiration, value)

    @override
    async def set(self, key: str, value: bytes | str) -> None:
        await self._client.set(key, value)

    @override
    async def get(self, key: str) -> bytes | None:
        return await self._client.get(key)

    async def close(self) -> None:
        await self._client.close()
