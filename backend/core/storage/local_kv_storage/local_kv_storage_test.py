# pyright: reportPrivateUsage=false


from datetime import timedelta

import pytest

from core.storage.local_kv_storage.local_kv_storage import LocalKVStorage


@pytest.fixture
async def local_storage():
    return LocalKVStorage()


class TestGet:
    async def test_get(self, local_storage: LocalKVStorage):
        await local_storage.set("test", "test")
        assert await local_storage.get("test") == "test"

    async def test_get_none(self, local_storage: LocalKVStorage):
        assert await local_storage.get("test") is None


class TestSet:
    async def test_set(self, local_storage: LocalKVStorage):
        await local_storage.set("test", "test")
        assert await local_storage.get("test") == "test"

    async def test_set_bytes(self, local_storage: LocalKVStorage):
        await local_storage.set("test", b"test")
        assert await local_storage.get("test") == b"test"


class TestSetEx:
    async def test_set_ex(self, local_storage: LocalKVStorage):
        await local_storage.setex("test", timedelta(seconds=1), "test")
        assert await local_storage.get("test") == "test"

    async def test_set_ex_bytes(self, local_storage: LocalKVStorage):
        await local_storage.setex("test", timedelta(seconds=1), b"test")
        assert await local_storage.get("test") == b"test"
