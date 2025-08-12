from collections.abc import Callable, Iterable

from structlog.typing import FilteringBoundLogger


def first_where[T](iterable: Iterable[T], condition: Callable[[T], bool], default: T | None = None) -> T | None:
    """Return the first item in 'iterable' that satisfies 'condition' if any, else return 'default'."""

    return next((item for item in iterable if condition(item)), default)


def last_where[T](iterable: Iterable[T], condition: Callable[[T], bool], default: T | None = None) -> T | None:
    """Return the last item in 'iterable' that satisfies 'condition' if any, else return 'default'."""

    return first_where(reversed(list(iterable)), condition, default)


def safe_map[T, T2](
    iterable: Iterable[T],
    func: Callable[[T], T2],
    logger: FilteringBoundLogger | None = None,
) -> list[T2]:
    """Map 'iterable' with 'func' and return a list of results, ignoring any errors."""

    results: list[T2] = []
    for item in iterable:
        try:
            results.append(func(item))
        except Exception as e:
            if logger:
                logger.exception(str(e))

    return results


def safe_map_optional[T, T2](
    iterable: Iterable[T] | None,
    func: Callable[[T], T2],
    logger: FilteringBoundLogger | None = None,
) -> list[T2] | None:
    if not iterable:
        return None

    return safe_map(iterable, func, logger) or None


def group_by[T, K](iterable: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    """Group 'iterable' by 'key' and return a dictionary of lists."""

    out: dict[K, list[T]] = {}
    for item in iterable:
        out.setdefault(key(item), []).append(item)

    return out
