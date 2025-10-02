# pyright: reportPrivateUsage=false


from datetime import timedelta

import pytest

from core.storage.redis.redis_storage import RedisStorage


@pytest.fixture
async def redis_storage():
    res = RedisStorage(dsn="redis://localhost:6379/10")
    await res._client.flushdb()
    yield res
    await res.close()


class TestGet:
    async def test_get(self, redis_storage: RedisStorage):
        await redis_storage._client.set("test", "test")
        assert await redis_storage.get("test") == b"test"

    async def test_get_none(self, redis_storage: RedisStorage):
        assert await redis_storage.get("test") is None


class TestSet:
    async def test_set(self, redis_storage: RedisStorage):
        await redis_storage.set("test", "test")
        assert await redis_storage._client.get("test") == b"test"
        # EXPIRETIME is not supported in redis 6.0


class TestSetEx:
    async def test_set_ex(self, redis_storage: RedisStorage):
        await redis_storage.setex("test", timedelta(seconds=1), "test")
        assert await redis_storage._client.get("test") == b"test"
        # Not sure how to check the expiration, we don't really want to wait 1s here
