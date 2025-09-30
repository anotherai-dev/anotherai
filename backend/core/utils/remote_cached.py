import functools
import hashlib
import pickle
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any, Protocol

from structlog import get_logger


class RemoteCache(Protocol):
    async def get(self, key: str) -> bytes | None: ...
    async def setex(self, key: str, expiration: timedelta, value: bytes) -> None: ...


def _generate_cache_key(
    func: Callable[..., Awaitable[Any]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    suffix: str = "",
) -> str:
    """
    Generate a cache key based on function and arguments.

    Args:
        func: The function being decorated
        args: Positional arguments to the function
        kwargs: Keyword arguments to the function
        suffix: Optional suffix to differentiate different types of caches

    Returns:
        str: Cache key string
    """
    # Use the original function, not the wrapper
    orig_func = getattr(func, "__wrapped__", func)

    # Get the function's qualified name to detect if it's a method
    is_method = False
    if hasattr(orig_func, "__qualname__") and "." in orig_func.__qualname__:
        is_method = True

    # Skip the first argument (self/cls) for methods
    args_to_hash = args[1:] if is_method and args else args

    # Generate hash from the args (excluding self/cls) and kwargs

    args_bytes: bytes = pickle.dumps((args_to_hash, kwargs))
    args_hash: str = hashlib.sha256(args_bytes).hexdigest()

    module_name: str = func.__module__
    func_name: str = func.__name__
    return f"{module_name}.{func_name}{suffix}:{args_hash}"


_log = get_logger(__name__)


async def _wrap[T](
    cache: RemoteCache,
    func: Callable[..., Awaitable[T]],
    expiration_seconds: timedelta,
    *args: Any,
    **kwargs: Any,
) -> T:
    try:
        cache_key = _generate_cache_key(func, args, kwargs)
    except Exception as e:  # noqa: BLE001
        _log.exception("Could not generate cache key", exc_info=e, func=func.__name__)
        return await func(*args, **kwargs)

    try:
        res = await cache.get(cache_key)
    except Exception as e:  # noqa: BLE001
        _log.exception("Could not get cached result", exc_info=e, func=func.__name__)
        res = None

    if res:
        try:
            return pickle.loads(res)  # noqa: S301
        except Exception as e:  # noqa: BLE001
            _log.exception("Could not deserialize cached result", exc_info=e, func=func.__name__)
            return await func(*args, **kwargs)

    result = await func(*args, **kwargs)
    try:
        await cache.setex(cache_key, expiration_seconds, pickle.dumps(result))
    except Exception as e:  # noqa: BLE001
        _log.exception("Could not set cached result", exc_info=e, func=func.__name__)
    return result


class _NoopCache(RemoteCache):
    async def get(self, key: str) -> bytes | None:
        return None

    async def setex(self, key: str, expiration: timedelta, value: bytes) -> None:
        pass


shared_cache = _NoopCache()


def remote_cached(expiration: timedelta | None = None, cache: RemoteCache | None = None):
    if not expiration:
        expiration = timedelta(seconds=60 * 60 * 24)
    if not cache:
        cache = shared_cache

    def decorator[F: Callable[..., Awaitable[Any]]](func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _wrap(shared_cache, func, expiration, *args, **kwargs)

        return async_wrapper  # pyright: ignore[reportReturnType]

    return decorator
