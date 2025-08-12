from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from core.domain.agent_completion import AgentCompletion


class Event(BaseModel):
    tenant: str = ""
    tenant_uid: int = 0


class StoreCompletionEvent(Event):
    completion: AgentCompletion


class EventRouter(Protocol):
    def __call__(self, event: Event, retry_after: datetime | None = None) -> None: ...
