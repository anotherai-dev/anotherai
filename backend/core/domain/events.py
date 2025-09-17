from typing import Protocol
from uuid import UUID

from pydantic import BaseModel

from core.domain.agent_completion import AgentCompletion


class Event(BaseModel):
    tenant_uid: int = 0


class StoreCompletionEvent(Event):
    completion: AgentCompletion


class UserConnectedEvent(Event):
    """Event sent when a user connected with a JWT"""

    # Change the default value. the user connected event should not have a tenant_uid
    tenant_uid: int = -1

    user_id: str
    organization_id: str | None


class StartExperimentCompletion(Event):
    experiment_id: str
    completion_id: UUID
    version_id: str
    input_id: str


class EventRouter(Protocol):
    def __call__(self, event: Event, delay: float | None = None) -> None: ...
