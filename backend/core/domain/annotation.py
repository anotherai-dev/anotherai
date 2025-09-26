from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from core.utils.fields import datetime_zero


class Annotation(BaseModel):
    id: str = ""
    created_at: datetime = Field(default_factory=datetime_zero)
    updated_at: datetime = Field(default_factory=datetime_zero)
    author_name: str

    class Target(BaseModel):
        completion_id: UUID | None = None
        experiment_id: str | None = None
        key_path: str | None = None

    target: Target | None = None

    class Context(BaseModel):
        agent_id: str | None = None
        experiment_id: str | None = None

    context: Context | None = None

    text: str | None = None

    class Metric(BaseModel):
        name: str
        value: float | str | bool

    metric: Metric | None

    metadata: dict[str, Any] | None = None

    def set_context_agent_id(self, agent_id: str) -> None:
        if not self.context:
            self.context = self.Context()
        self.context.agent_id = agent_id
