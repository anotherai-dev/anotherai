from types import CoroutineType
from typing import Any, Concatenate

from taskiq import AsyncTaskiqDecoratedTask

type TASK[T] = AsyncTaskiqDecoratedTask[Concatenate[T, ...], CoroutineType[Any, Any, None]]
