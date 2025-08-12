from asyncio import Protocol
from contextvars import ContextVar
from typing import Any

from core.providers._base.llm_completion import LLMCompletion


class BuilderInterface(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def llm_completions(self) -> list[LLMCompletion]: ...

    def add_metadata(self, key: str, value: Any) -> None: ...

    def get_metadata(self, key: str) -> Any | None: ...

    def record_file_download_seconds(self, seconds: float) -> None: ...


builder_context = ContextVar[BuilderInterface | None]("builder_context", default=None)
