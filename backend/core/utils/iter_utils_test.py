
from typing import Any

import structlog

from core.utils.iter_utils import first_where, last_where, safe_map


def test_first_where_condition_met() -> None:
    # Test that it returns the first item satisfying the condition
    iterable = [1, 2, 3, 4, 5]
    assert first_where(iterable, lambda x: x > 3) == 4


def test_last_where_condition_met() -> None:
    # Test that it returns the last item satisfying the condition
    iterable = [1, 2, 3, 4, 5]
    assert last_where(iterable, lambda x: x > 3) == 5


def test_first_where_condition_not_met() -> None:
    # Test that it returns the default value when no item satisfies the condition
    iterable = [1, 2, 3]
    default = -1
    assert first_where(iterable, lambda x: x > 5, default) == default


def test_last_where_condition_not_met() -> None:
    # Test that it returns the default value when no item satisfies the condition
    iterable = [1, 2, 3]
    default = -1
    assert last_where(iterable, lambda x: x > 5, default) == default


def test_first_where_condition_not_met_none_default() -> None:
    # Test that it returns the default value (=None) when no item satisfies the condition
    iterable = [1, 2, 3]
    assert first_where(iterable, lambda x: x > 5) is None


def test_last_where_condition_not_met_none_default() -> None:
    # Test that it returns the default value (=None) when no item satisfies the condition
    iterable = [1, 2, 3]
    assert last_where(iterable, lambda x: x > 5) is None


def test_first_where_empty_iterable() -> None:
    # Test that it returns the default value when the iterable is empty
    iterable: list[Any] = []
    default = -1
    assert first_where(iterable, lambda x: x > 0, default) == default


def test_last_where_empty_iterable() -> None:
    # Test that it returns the default value when the iterable is empty
    iterable: list[Any] = []
    default = -1
    assert last_where(iterable, lambda x: x > 0, default) == default


def test_first_where_different_iterable_type() -> None:
    # Test that it works with different iterable types, e.g., a set
    iterable = {10, 20, 30, 40}
    assert first_where(iterable, lambda x: x == 20) == 20


def test_last_where_different_iterable_type() -> None:
    # Test that it works with different iterable types, e.g., a set
    iterable = {10, 20, 30, 40}
    assert last_where(iterable, lambda x: x == 20) == 20


def test_safe_map_successful_mapping() -> None:
    # Test that it correctly maps items when no errors occur
    iterable = [1, 2, 3]
    logger = structlog.get_logger(__name__)
    result = safe_map(iterable, lambda x: x * 2, logger)
    assert result == [2, 4, 6]


def test_safe_map_with_errors() -> None:
    # Test that it skips items that cause errors
    def transform(x: int) -> int:
        if x == 2:
            raise ValueError("Error processing 2")
        return x * 2

    iterable = [1, 2, 3]
    logger = structlog.get_logger(__name__)
    result = safe_map(iterable, transform, logger)
    assert result == [2, 6]  # 2 is skipped due to error


def test_safe_map_empty_iterable() -> None:
    # Test that it handles empty iterables correctly
    iterable: list[int] = []
    logger = structlog.get_logger(__name__)
    result = safe_map(iterable, lambda x: x * 2, logger)
    assert result == []


def test_safe_map_different_types() -> None:
    # Test that it works with different input and output types
    iterable = ["1", "2", "3"]
    logger = structlog.get_logger(__name__)
    result = safe_map(iterable, int, logger)
    assert result == [1, 2, 3]


def test_safe_map_all_errors() -> None:
    # Test that it returns an empty list when all items cause errors
    def always_fail(_: int) -> int:
        raise ValueError("Always fails")

    iterable = [1, 2, 3]
    logger = structlog.get_logger(__name__)
    result = safe_map(iterable, always_fail, logger)
    assert result == []
