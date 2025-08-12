from datetime import datetime

from pydantic import BaseModel, Field

from core.utils.fields import datetime_zero


class Agent(BaseModel):
    id: str
    uid: int
    name: str = ""
    created_at: datetime = Field(default_factory=datetime_zero)
