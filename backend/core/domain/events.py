from typing import Protocol

from pydantic import BaseModel

from core.domain.agent_completion import AgentCompletion


class Event(BaseModel):
    tenant_uid: int = 0


class StoreCompletionEvent(Event):
    completion: AgentCompletion


class EventRouter(Protocol):
    def __call__(self, event: Event, delay: float | None = None) -> None: ...
