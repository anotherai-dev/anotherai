import json
import uuid
from typing import Any, override

from asyncpg.pool import PoolConnectionProxy
from pydantic import ValidationError
from structlog import get_logger

from core.domain.exceptions import ObjectNotFoundError
from core.domain.view import Graph, View, ViewFolder
from core.storage.psql._psql_base_storage import JSONDict, PsqlBaseRow, PsqlBaseStorage
from core.storage.psql._psql_utils import set_values
from core.storage.view_storage import ViewStorage
from core.utils.iter_utils import safe_map

_log = get_logger(__name__)


class PsqlViewStorage(PsqlBaseStorage, ViewStorage):
    @override
    @classmethod
    def table(cls) -> str:
        return "views"

    @override
    async def create_view_folder(self, folder: ViewFolder):
        if not folder.id:
            folder.id = str(uuid.uuid4())
        view_folder_row = _ViewFolderRow.from_domain(folder)
        async with self._connect() as connection:
            id = await self._insert(connection, view_folder_row, table="view_folders")
            if folder.views:
                # TODO: Doing an n+1 here, not great, but that should rarely happen
                for i, view in enumerate(folder.views):
                    if not view.id:
                        view.id = str(uuid.uuid4())
                    view.folder_id = folder.id
                    view.position = i
                    view_row = _ViewRow.from_domain(view, id)
                    _ = await self._insert(connection, view_row, table="views")

    @override
    async def list_views(self) -> list[View]:
        async with self._connect() as connection:
            rows = await connection.fetch("SELECT * FROM views WHERE deleted_at IS NULL")
            return safe_map(rows, lambda x: self._validate(_ViewRow, x).to_domain(None), _log)

    @override
    async def list_view_folders(self, include_views: bool = True) -> list[ViewFolder]:
        async with self._connect() as connection:
            rows = await connection.fetch("SELECT * FROM view_folders WHERE deleted_at IS NULL")

            if include_views:
                views = await connection.fetch(
                    "SELECT * FROM views WHERE deleted_at IS NULL ORDER BY (position, updated_at)",
                )
                views_by_folder_id: dict[int, list[View]] = {}
                for row in views:
                    try:
                        validated = self._validate(_ViewRow, row).to_domain(None)
                    except ValidationError:
                        _log.exception("Invalid view in database", row=row)
                        continue
                    views_by_folder_id.setdefault(row["folder_uid"] or 0, []).append(validated)
            else:
                views_by_folder_id = {}

            arr = safe_map(
                rows,
                lambda x: self._validate(_ViewFolderRow, x).to_domain(views_by_folder_id.get(x["uid"], [])),
                _log,
            )
            if 0 in views_by_folder_id:
                arr.append(ViewFolder(id="", name="", views=views_by_folder_id[0]))
            return arr

    @override
    async def update_folder(self, folder_id: str, name: str | None) -> None:
        async with self._connect() as connection:
            _ = await connection.execute(
                "UPDATE view_folders SET name = $1 WHERE slug = $2",
                name,
                folder_id,
            )

    @override
    async def delete_folder(self, folder_id: str, delete_views: bool = True) -> None:
        async with self._connect() as connection:
            uid = await connection.fetchval(
                "UPDATE view_folders SET deleted_at = CURRENT_TIMESTAMP WHERE slug = $1 RETURNING uid",
                folder_id,
            )
            if not uid:
                return
            if delete_views:
                await connection.execute(
                    "UPDATE views SET deleted_at = CURRENT_TIMESTAMP WHERE folder_uid = $1",
                    uid,
                )
            else:
                await connection.execute(
                    "UPDATE views SET folder_uid = NULL WHERE folder_uid = $1",
                    uid,
                )

    async def _folder_uid(self, connection: PoolConnectionProxy, folder_id: str) -> int:
        uid = await connection.fetchval(
            "SELECT uid FROM view_folders WHERE slug = $1 AND deleted_at IS NULL",
            folder_id,
        )
        if not uid:
            raise ObjectNotFoundError(object_type="view_folder")
        return uid

    @override
    async def create_or_replace_view(self, view: View):
        if not view.id:
            # generating a random id for the view
            view.id = str(uuid.uuid4())

        async with self._connect() as connection:
            if view.folder_id:
                folder_uid = await self._folder_uid(connection, view.folder_id)
            else:
                folder_uid = None

            if view.position is None:
                # This could create race conditions, but we are ok with that for now
                view.position = await connection.fetchval(
                    "SELECT COUNT(*) FROM views WHERE folder_uid = $1 AND deleted_at IS NULL",
                    folder_uid,
                )

            view_row = _ViewRow.from_domain(view, folder_uid)
            _ = await self._insert(
                connection,
                view_row,
                on_conflict="""ON CONFLICT (tenant_uid, slug) DO UPDATE
    SET updated_at = CURRENT_TIMESTAMP,
    title = EXCLUDED.title,
    query = EXCLUDED.query,
    folder_uid = EXCLUDED.folder_uid,
    graph_type = EXCLUDED.graph_type,
    graph = EXCLUDED.graph""",
                table="views",
            )

    @override
    async def retrieve_view(self, view_id: str) -> View:
        async with self._connect() as connection:
            row = await connection.fetchrow(
                """
                SELECT views.*, view_folders.slug as folder_slug FROM views
                LEFT JOIN view_folders ON views.folder_uid = view_folders.uid
                WHERE views.slug = $1 AND views.deleted_at IS NULL
                """,
                view_id,
            )
            if not row:
                raise ObjectNotFoundError(object_type="view")
            return self._validate(_ViewRow, row).to_domain(folder_id=row["folder_slug"])

    @override
    async def update_view(
        self,
        view_id: str,
        title: str | None,
        query: str | None,
        graph: Graph | None,
        folder_id: str | None,
        position: int | None,
    ) -> None:
        updates: list[tuple[str, Any]] = [
            ("title", title),
            ("query", query),
            ("position", position),
        ]
        if graph:
            updates.append(("graph_type", graph.type))
            updates.append(("graph", json.dumps(graph.attributes or {})))

        async with self._connect() as connection:
            if folder_id:
                folder_uid = await self._folder_uid(connection, folder_id)
                updates.append(("folder_uid", folder_uid))
            elif folder_id == "":
                updates.append(("folder_uid", None))
            sets, set_args = set_values(updates, start=2, keep_none=lambda v: v[0] == "folder_uid")
            _ = await connection.execute(
                f"""
                UPDATE views SET {sets} WHERE slug = $1
                """,  # noqa: S608
                view_id,
                *set_args,
            )

    @override
    async def delete_view(self, view_id: str) -> None:
        async with self._connect() as connection:
            _ = await connection.execute(
                """
                UPDATE views SET deleted_at = CURRENT_TIMESTAMP WHERE slug = $1
                """,
                view_id,
            )


class _ViewRow(PsqlBaseRow):
    slug: str = ""
    title: str = ""
    query: str = ""
    position: int = 0
    folder_uid: int | None = None
    graph_type: str = ""
    graph: JSONDict | None = None

    def _domain_graph(self) -> Graph | None:
        if not self.graph or not self.graph_type:
            return None
        try:
            return Graph(type=self.graph_type, attributes=self.graph)
        except ValidationError:
            _log.exception("Invalid graph in database")
            return None

    def to_domain(self, folder_id: str | None) -> View:
        return View(
            id=self.slug,
            title=self.title,
            query=self.query,
            graph=self._domain_graph(),
            position=self.position,
            folder_id=folder_id,
        )

    @classmethod
    def from_domain(cls, view: View, folder_uid: int | None):
        return cls(
            slug=view.id,
            title=view.title or "",
            query=view.query or "",
            folder_uid=folder_uid or None,
            graph_type=view.graph.type if view.graph else "",
            graph=view.graph.attributes if view.graph and view.graph.attributes else None,
            position=view.position or 0,
        )


class _ViewFolderRow(PsqlBaseRow):
    slug: str = ""
    name: str = ""

    @classmethod
    def from_domain(cls, folder: ViewFolder):
        return cls(
            slug=folder.id,
            name=folder.name,
        )

    def to_domain(self, views: list[View] | None = None) -> ViewFolder:
        return ViewFolder(
            id=self.slug,
            name=self.name,
            views=views,
        )
