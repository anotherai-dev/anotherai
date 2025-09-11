from typing import Protocol

from pydantic import BaseModel

from core.domain.agent_completion import AgentCompletion


class Event(BaseModel):
    tenant_uid: int = 0


class StoreCompletionEvent(Event):
    completion: AgentCompletion


class UserConnectedEvent(Event):
    """Event sent when a user connected with a JWT"""

    user_id: str
    organization_id: str | None


class EventRouter(Protocol):
    def __call__(self, event: Event, delay: float | None = None) -> None: ...
