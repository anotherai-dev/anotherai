from collections.abc import Callable
from datetime import datetime
from typing import Any

# def _sets(self, values: list[tuple[str, Any]], start: int = 1) -> tuple[str, list[Any]]:
#         columns: list[str] = []
#         args: list[Any] = []
#         for v in values:
#             if v[-1] is None:
#                 # Skipping None values
#                 continue
#             columns.append(f"{v[0]} = ${start}")
#             args.append(self._map_value(v[-1]))
#             start += 1
#         return ", ".join(columns), args


def map_value(v: Any) -> Any:
    match v:
        case datetime():
            return v.replace(tzinfo=None) if v.tzinfo else v
        case _:
            return v


def set_values(
    values: list[tuple[str, Any]],
    start: int = 1,
    keep_none: Callable[[tuple[str, Any]], bool] | None = None,
) -> tuple[str, list[Any]]:
    columns: list[str] = []
    args: list[Any] = []
    if not keep_none:
        keep_none = lambda _: False  # noqa: E731

    for v in values:
        if not keep_none(v) and v[-1] is None:
            # Skipping None values
            continue
        columns.append(f"{v[0]} = ${start}")
        args.append(map_value(v[-1]))
        start += 1
    return ", ".join(columns), args
