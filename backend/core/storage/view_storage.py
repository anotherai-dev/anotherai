from typing import Protocol

from core.domain.view import Graph, View, ViewFolder


class ViewStorage(Protocol):
    async def create_view_folder(self, folder: ViewFolder): ...

    async def list_view_folders(self, include_views: bool = True) -> list[ViewFolder]: ...

    async def list_views(self) -> list[View]: ...

    async def update_folder(self, folder_id: str, name: str | None) -> None: ...

    async def delete_folder(self, folder_id: str, delete_views: bool = False) -> None: ...

    async def create_or_replace_view(self, view: View): ...

    async def retrieve_view(self, view_id: str) -> View: ...

    async def update_view(
        self,
        view_id: str,
        title: str | None,
        query: str | None,
        graph: Graph | None,
        folder_id: str | None,
        position: int | None,
    ) -> None: ...

    async def delete_view(self, view_id: str) -> None: ...
