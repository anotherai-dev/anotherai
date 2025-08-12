from datetime import datetime

from pydantic import BaseModel


class APIKey(BaseModel):
    id: str
    name: str
    partial_key: str
    created_at: datetime
    last_used_at: datetime | None
    created_by: str


class CompleteAPIKey(APIKey):
    api_key: str
