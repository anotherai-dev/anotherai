# pyright: reportPrivateUsage=false

import pickle
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from core.utils.remote_cached import RemoteCache, _wrap


@pytest.fixture
def mock_cache():
    return Mock(spec=RemoteCache)


@pytest.fixture
def mock_fn():
    return AsyncMock(return_value=10)


class TestWrap:
    async def test_cache_get_error_not_propagated(self, mock_cache: Mock, mock_fn: AsyncMock):
        """Test that errors from cache.get() are not propagated."""
        # Setup
        mock_cache.get.side_effect = Exception("Cache connection error")

        # Execute
        result = await _wrap(mock_cache, mock_fn, timedelta(seconds=60), 5)

        # Verify
        assert result == 10
        mock_cache.get.assert_awaited_once()
        mock_fn.assert_awaited_once()

    async def test_cache_setex_error_not_propagated(self, mock_cache: Mock, mock_fn: AsyncMock):
        """Test that errors from cache.setex() are not propagated."""
        # Setup
        mock_cache.get.return_value = None
        mock_cache.setex.side_effect = Exception("Cache write error")

        # Execute
        result = await _wrap(mock_cache, mock_fn, timedelta(seconds=60), 5)

        # Verify
        assert result == 10
        mock_cache.get.assert_awaited_once()
        mock_cache.setex.assert_awaited_once()
        mock_fn.assert_awaited_once()

    async def test_deserialization_error_not_propagated(self, mock_cache: Mock, mock_fn: AsyncMock):
        """Test that errors during deserialization are not propagated."""
        # Setup - return invalid cached data
        mock_cache.get.return_value = b"invalid pickle data"

        # Execute
        result = await _wrap(mock_cache, mock_fn, timedelta(seconds=60), 5)

        # Verify - function should be called and return correct value
        assert result == 10
        mock_cache.get.assert_awaited_once()
        mock_fn.assert_awaited_once()

    async def test_cache_key_generation_error_not_propagated(self, mock_cache: Mock, mock_fn: AsyncMock):
        """Test that errors during cache key generation are not propagated."""

        # Create an unpicklable object to cause cache key generation to fail
        class UnpicklableClass:
            def __reduce__(self):
                raise Exception("Cannot pickle")

        unpicklable = UnpicklableClass()

        result = await _wrap(mock_cache, mock_fn, timedelta(seconds=60), unpicklable)

        # Verify - function should still be called
        assert result == 10
        # Cache should not be called since key generation failed
        mock_cache.get.assert_not_awaited()
        mock_fn.assert_awaited_once()

    async def test_successful_cache_hit(self, mock_cache: Mock, mock_fn: AsyncMock):
        """Test that cached values are returned correctly."""
        # Setup
        cached_value = pickle.dumps(100)
        mock_cache.get.return_value = cached_value

        # Execute
        result = await _wrap(mock_cache, mock_fn, timedelta(seconds=60), 5)

        # Verify
        assert result == 100
        mock_fn.assert_not_awaited()
        mock_cache.get.assert_awaited_once()
        mock_cache.setex.assert_not_awaited()

    async def test_successful_cache_miss_and_set(self, mock_cache: Mock, mock_fn: AsyncMock):
        """Test that on cache miss, the function is called and result is cached."""
        # Setup
        mock_cache.get.return_value = None
        mock_cache.setex.return_value = None
        mock_fn.return_value = 10
        mock_fn.assert_not_awaited()

        # Execute
        result = await _wrap(mock_cache, mock_fn, timedelta(seconds=60), 5)

        # Verify
        assert result == 10
        mock_cache.get.assert_awaited_once()
        mock_cache.setex.assert_awaited_once()
        mock_fn.assert_awaited_once()
        # Verify the cached value
        call_args = mock_cache.setex.await_args
        assert call_args[0][1] == timedelta(seconds=60)
