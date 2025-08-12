from pydantic import BaseModel


class UserIdentifier(BaseModel):
    user_id: str | None = None
    user_email: str | None = None
