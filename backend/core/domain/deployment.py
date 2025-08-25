from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from core.domain.version import Version
from core.utils.fields import datetime_factory


class Deployment(BaseModel):
    id: str
    agent_id: str
    version: Version
    created_at: datetime = Field(default_factory=datetime_factory)
    updated_at: datetime | None = None
    metadata: dict[str, Any] | None
