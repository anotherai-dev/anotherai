from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from core.domain.annotation import Annotation
from core.utils.fields import datetime_zero


class Experiment(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime_zero)
    updated_at: datetime = Field(default_factory=datetime_zero)
    author_name: str

    title: str
    description: str
    result: str | None
    agent_id: str

    run_ids: list[str] = Field(default_factory=list)

    annotations: list[Annotation] = Field(default_factory=list)

    metadata: dict[str, Any] | None
