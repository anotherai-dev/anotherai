from pydantic import BaseModel


class Page[T](BaseModel):
    items: list[T]
    count: int | None = None
    previous_page_token: str | None = None
    next_page_token: str | None = None
