from typing import Any

from pydantic import BaseModel


class Graph(BaseModel):
    type: str = ""
    attributes: dict[str, Any] | None = None


class View(BaseModel):
    id: str = ""
    title: str | None = None
    query: str | None = None
    graph: Graph | None = None

    folder_id: str | None = None
    position: int | None = None


class ViewFolder(BaseModel):
    id: str = ""
    name: str = ""
    views: list[View] | None = None
