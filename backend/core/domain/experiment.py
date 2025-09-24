from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from core.domain.agent_input import AgentInput
from core.domain.agent_output import AgentOutput
from core.domain.annotation import Annotation
from core.domain.cache_usage import CacheUsage
from core.domain.version import Version
from core.utils.fields import datetime_zero


class ExperimentOutput(BaseModel):
    completion_id: UUID
    version_id: str
    input_id: str
    created_at: datetime = Field(default_factory=datetime_zero)
    started_at: datetime | None
    completed_at: datetime | None
    output: AgentOutput | None
    cost_usd: float | None
    duration_seconds: float | None


class Experiment(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=datetime_zero)
    updated_at: datetime = Field(default_factory=datetime_zero)
    author_name: str

    title: str
    description: str
    result: str | None
    agent_id: str

    use_cache: CacheUsage | None = None

    run_ids: list[str] = Field(default_factory=list)

    annotations: list[Annotation] = Field(default_factory=list)

    metadata: dict[str, Any] | None = None

    versions: list[Version] | None = None

    inputs: list[AgentInput] | None = None

    outputs: list[ExperimentOutput] | None = None
