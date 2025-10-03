from typing import final

from structlog import get_logger

from core.domain.exceptions import BadRequestError, ObjectNotFoundError
from core.storage.completion_storage import CompletionStorage
from core.storage.view_storage import ViewStorage
from core.utils.iter_utils import safe_map
from protocol.api._api_models import (
    CreateViewRequest,
    CreateViewResponse,
    Page,
    PatchViewFolderRequest,
    PatchViewRequest,
    View,
    ViewFolder,
)
from protocol.api._services.conversions import (
    graph_to_domain,
    view_folder_from_domain,
    view_folder_to_domain,
    view_from_domain,
    view_to_create_view_response,
    view_to_domain,
)

_log = get_logger(__name__)


@final
class ViewService:
    def __init__(
        self,
        view_storage: ViewStorage,
        completion_storage: CompletionStorage,
    ):
        self._view_storage = view_storage
        self._completion_storage = completion_storage

    async def list_view_folders(self) -> Page[ViewFolder]:
        view_folders = await self._view_storage.list_view_folders()
        return Page(
            items=[view_folder_from_domain(v) for v in view_folders],
            total=len(view_folders),
        )

    async def list_views(self) -> Page[View]:
        views = await self._view_storage.list_views()
        return Page(
            items=safe_map(views, view_from_domain, _log),
            total=len(views),
        )

    async def get_view(self, view_id: str) -> View:
        view = await self._view_storage.retrieve_view(view_id)
        return view_from_domain(view)

    async def patch_view_folder(self, view_folder_id: str, req: PatchViewFolderRequest):
        await self._view_storage.update_folder(view_folder_id, req.name)

    async def create_view_folder(self, view_folder: ViewFolder) -> ViewFolder:
        created = view_folder_to_domain(view_folder)
        await self._view_storage.create_view_folder(created)
        return view_folder_from_domain(created)

    async def delete_view_folder(self, view_folder_id: str):
        await self._view_storage.delete_folder(view_folder_id, delete_views=True)

    async def patch_view(self, view_id: str, req: PatchViewRequest) -> View:
        if req.query:
            await self._validate_query(req.query)
        await self._view_storage.update_view(
            view_id,
            req.title,
            req.query,
            graph_to_domain(req.graph) if req.graph else None,
            folder_id=req.folder_id,
            position=req.position,
        )
        return await self.get_view(view_id)

    async def delete_view(self, view_id: str):
        await self._view_storage.delete_view(view_id)

    async def _validate_query(self, query: str):
        try:
            _ = await self._completion_storage.raw_query(query.replace("{limit}", "1").replace("{offset}", "0"))
        except Exception as e:
            raise BadRequestError(f"Invalid query: {e!s}") from e

    async def create_view(self, view: CreateViewRequest | View) -> View:
        # Attempt to fetch the completions
        await self._validate_query(view.query)
        v = view_to_domain(view)
        if isinstance(view, CreateViewRequest):
            v.folder_id = view.folder_id

        await self._view_storage.create_or_replace_view(v)
        return view_from_domain(v)

    async def create_or_update_mcp(self, view: View) -> CreateViewResponse:
        # Validate the query first
        await self._validate_query(view.query)

        # Check if view exists and preserve its folder_id
        try:
            existing_view = await self._view_storage.retrieve_view(view.id)
            # Convert to domain view and preserve the existing folder_id
            domain_view = view_to_domain(view)
            domain_view.folder_id = existing_view.folder_id
            await self._view_storage.create_or_replace_view(domain_view)
            created_view = view_from_domain(domain_view)
        except ObjectNotFoundError:
            # View doesn't exist, create it normally
            created_view = await self.create_view(view)

        return view_to_create_view_response(created_view)
