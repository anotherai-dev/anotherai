from collections.abc import Callable
from typing import Any

type OutputFactory = Callable[[str], Any]
