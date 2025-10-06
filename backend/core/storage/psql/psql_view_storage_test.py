# pyright: reportPrivateUsage=false
import json

import asyncpg
import pytest

from core.domain.exceptions import ObjectNotFoundError
from core.domain.view import Graph, View, ViewFolder
from core.storage.psql.psql_view_storage import PsqlViewStorage
from tests.fake_models import fake_graph


@pytest.fixture
async def view_storage(inserted_tenant: int, purged_psql: asyncpg.Pool):
    return PsqlViewStorage(tenant_uid=inserted_tenant, pool=purged_psql)


async def _insert_view_folder(conn: asyncpg.Connection, slug: str = "test-folder", name: str | None = None) -> int:
    if not name:
        name = f"Test Folder {slug}"
    folder_uid = await conn.fetchval(
        "INSERT INTO view_folders (slug, name) VALUES ($1, $2) RETURNING uid",
        slug,
        name,
    )
    return folder_uid


async def _insert_view(
    conn: asyncpg.Connection,
    slug: str = "test-view",
    title: str | None = None,
    query: str = "SELECT 1",
    folder_uid: int | None = None,
    position: int = 0,
):
    if not title:
        title = f"Test View {slug}"
    _ = await conn.execute(
        "INSERT INTO views (slug, title, query, folder_uid, position) VALUES ($1, $2, $3, $4, $5)",
        slug,
        title,
        query,
        folder_uid,
        position,
    )


class TestCreateViewFolder:
    async def test_create_view_folder_without_views(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        folder = ViewFolder(id="test-folder", name="Test Folder", views=None)

        await view_storage.create_view_folder(folder)

        # Verify folder was created in database
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT slug, name FROM view_folders WHERE slug = $1",
            "test-folder",
        )
        assert row is not None
        assert row["slug"] == "test-folder"
        assert row["name"] == "Test Folder"

    async def test_create_view_folder_with_views(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        views = [
            View(id="view-1", title="View 1", query="SELECT 1"),
            View(id="view-2", title="View 2", query="SELECT 2"),
        ]
        folder = ViewFolder(id="test-folder", name="Test Folder", views=views)

        await view_storage.create_view_folder(folder)

        # Verify folder was created
        folder_row = await purged_psql_tenant_conn.fetchrow(
            "SELECT slug, name FROM view_folders WHERE slug = $1",
            "test-folder",
        )
        assert folder_row is not None

        # Verify views were created with correct positions and folder_uid
        view_rows = await purged_psql_tenant_conn.fetch(
            "SELECT slug, title, query, position, folder_uid FROM views WHERE folder_uid = (SELECT uid FROM view_folders WHERE slug = $1) ORDER BY position",
            "test-folder",
        )
        assert len(view_rows) == 2
        assert view_rows[0]["slug"] == "view-1"
        assert view_rows[0]["position"] == 0
        assert view_rows[1]["slug"] == "view-2"
        assert view_rows[1]["position"] == 1

    async def test_create_view_folder_generates_id_if_missing(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        folder = ViewFolder(id="", name="Test Folder")

        await view_storage.create_view_folder(folder)

        # Verify folder was created with generated ID
        rows = await purged_psql_tenant_conn.fetch("SELECT slug FROM view_folders WHERE name = $1", "Test Folder")
        assert len(rows) == 1
        assert rows[0]["slug"] != ""
        assert len(rows[0]["slug"]) > 0

    async def test_create_view_folder_generates_view_ids_if_missing(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        views = [View(id="", title="View 1", query="SELECT 1")]
        folder = ViewFolder(id="test-folder", name="Test Folder", views=views)

        await view_storage.create_view_folder(folder)

        # Verify view was created with generated ID
        view_rows = await purged_psql_tenant_conn.fetch(
            "SELECT slug FROM views WHERE folder_uid = (SELECT uid FROM view_folders WHERE slug = $1)",
            "test-folder",
        )
        assert len(view_rows) == 1
        assert view_rows[0]["slug"] != ""
        assert len(view_rows[0]["slug"]) > 0


class TestListViewFolders:
    async def test_list_view_folders_without_views(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder directly
        await _insert_view_folder(purged_psql_tenant_conn, "test-folder")

        folders = await view_storage.list_view_folders(include_views=False)

        assert len(folders) == 1
        assert folders[0].id == "test-folder"
        assert folders[0].name == "Test Folder test-folder"
        assert not folders[0].views

    async def test_list_view_folders_with_views(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder and views directly
        folder_uid = await _insert_view_folder(purged_psql_tenant_conn, "test-folder")
        await _insert_view(purged_psql_tenant_conn, "view-1", folder_uid=folder_uid, position=0)
        await _insert_view(purged_psql_tenant_conn, "view-2", folder_uid=folder_uid, position=1)

        folders = await view_storage.list_view_folders(include_views=True)

        assert len(folders) == 1
        folder = folders[0]
        assert folder.id == "test-folder"
        assert folder.name == "Test Folder test-folder"
        assert folder.views is not None
        assert len(folder.views) == 2
        assert folder.views[0].id == "view-1"
        assert folder.views[0].position == 0
        assert folder.views[1].id == "view-2"
        assert folder.views[1].position == 1

    async def test_list_view_folders_with_no_folders(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        folder_uid = await _insert_view_folder(purged_psql_tenant_conn, "test-folder")
        await _insert_view(purged_psql_tenant_conn, "view-1", folder_uid=folder_uid)
        await _insert_view(purged_psql_tenant_conn, "view-2", folder_uid=folder_uid, position=1)

        folder_uid2 = await _insert_view_folder(purged_psql_tenant_conn, "test-folder2")
        await _insert_view(purged_psql_tenant_conn, "view-3", folder_uid=folder_uid2, position=0)

        # No folder
        await _insert_view(purged_psql_tenant_conn, "view-4", folder_uid=None, position=0)

        folders = await view_storage.list_view_folders(include_views=True)

        assert len(folders) == 3
        assert folders[0].id == "test-folder"
        assert folders[0].name == "Test Folder test-folder"
        assert folders[1].id == "test-folder2"
        assert folders[1].name == "Test Folder test-folder2"
        assert folders[2].id == ""
        assert folders[2].views
        assert [v.id for v in folders[2].views] == ["view-4"]

    async def test_list_view_folders_excludes_deleted(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folders, one deleted
        await purged_psql_tenant_conn.execute(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2)",
            "active-folder",
            "Active Folder",
        )
        await purged_psql_tenant_conn.execute(
            "INSERT INTO view_folders (slug, name, deleted_at) VALUES ($1, $2, CURRENT_TIMESTAMP)",
            "deleted-folder",
            "Deleted Folder",
        )

        folders = await view_storage.list_view_folders()

        assert len(folders) == 1
        assert folders[0].id == "active-folder"

    async def test_list_view_folders_excludes_deleted_views_in_folders(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder
        folder_uid = await _insert_view_folder(purged_psql_tenant_conn, "test-folder")

        # Insert views - some active, some deleted
        await _insert_view(purged_psql_tenant_conn, "active-view-1", folder_uid=folder_uid, position=0)
        await _insert_view(purged_psql_tenant_conn, "active-view-2", folder_uid=folder_uid, position=1)

        # Insert deleted view directly in database
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, folder_uid, position, deleted_at) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)",
            "deleted-view-1",
            "Deleted View 1",
            "SELECT 1",
            folder_uid,
            2,
        )

        folders = await view_storage.list_view_folders(include_views=True)

        assert len(folders) == 1
        folder = folders[0]
        assert folder.id == "test-folder"
        assert folder.views is not None
        assert len(folder.views) == 2  # Only active views should be returned
        assert [v.id for v in folder.views] == ["active-view-1", "active-view-2"]

    async def test_list_view_folders_excludes_deleted_views_without_folders(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert views without folders (folder_uid = None) - some active, some deleted
        await _insert_view(purged_psql_tenant_conn, "active-view-1", folder_uid=None, position=0)
        await _insert_view(purged_psql_tenant_conn, "active-view-2", folder_uid=None, position=1)

        # Insert deleted view without folder directly in database
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, folder_uid, position, deleted_at) VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP)",
            "deleted-view-1",
            "Deleted View 1",
            "SELECT 1",
            None,
            2,
        )

        folders = await view_storage.list_view_folders(include_views=True)

        # Should return the root folder (id="") with only active views
        root_folder = next((f for f in folders if f.id == ""), None)
        assert root_folder is not None
        assert root_folder.views is not None
        assert len(root_folder.views) == 2  # Only active views should be returned
        assert [v.id for v in root_folder.views] == ["active-view-1", "active-view-2"]


class TestUpdateFolder:
    async def test_update_folder_name(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder
        await purged_psql_tenant_conn.execute(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2)",
            "test-folder",
            "Original Name",
        )

        await view_storage.update_folder("test-folder", "Updated Name")

        # Verify folder was updated
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT name FROM view_folders WHERE slug = $1",
            "test-folder",
        )
        assert row is not None
        assert row["name"] == "Updated Name"

    async def test_update_folder_nonexistent(
        self,
        view_storage: PsqlViewStorage,
    ):
        # Should not raise an error for non-existent folder
        await view_storage.update_folder("nonexistent", "New Name")


class TestDeleteFolder:
    async def test_delete_folder_with_delete_views_true(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder with views
        folder_uid = await purged_psql_tenant_conn.fetchval(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2) RETURNING uid",
            "test-folder",
            "Test Folder",
        )
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, folder_uid) VALUES ($1, $2, $3, $4)",
            "test-view",
            "Test View",
            "SELECT 1",
            folder_uid,
        )

        await view_storage.delete_folder("test-folder", delete_views=True)

        # Verify folder and views are marked as deleted
        folder_row = await purged_psql_tenant_conn.fetchrow(
            "SELECT deleted_at FROM view_folders WHERE slug = $1",
            "test-folder",
        )
        assert folder_row is not None
        assert folder_row["deleted_at"] is not None

        view_row = await purged_psql_tenant_conn.fetchrow(
            "SELECT deleted_at FROM views WHERE slug = $1",
            "test-view",
        )
        assert view_row is not None
        assert view_row["deleted_at"] is not None

    async def test_delete_folder_with_delete_views_false(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder with views
        folder_uid = await purged_psql_tenant_conn.fetchval(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2) RETURNING uid",
            "test-folder",
            "Test Folder",
        )
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, folder_uid) VALUES ($1, $2, $3, $4)",
            "test-view",
            "Test View",
            "SELECT 1",
            folder_uid,
        )

        await view_storage.delete_folder("test-folder", delete_views=False)

        # Verify folder is deleted but view is unlinked (folder_uid set to NULL)
        folder_row = await purged_psql_tenant_conn.fetchrow(
            "SELECT deleted_at FROM view_folders WHERE slug = $1",
            "test-folder",
        )
        assert folder_row is not None
        assert folder_row["deleted_at"] is not None

        view_row = await purged_psql_tenant_conn.fetchrow(
            "SELECT folder_uid, deleted_at FROM views WHERE slug = $1",
            "test-view",
        )
        assert view_row is not None
        assert view_row["folder_uid"] is None
        assert view_row["deleted_at"] is None

    async def test_delete_folder_nonexistent(
        self,
        view_storage: PsqlViewStorage,
    ):
        # Should not raise an error for non-existent folder
        await view_storage.delete_folder("nonexistent")


class TestCreateOrReplaceView:
    async def test_create_view_without_folder(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        view = View(
            id="test-view",
            title="Test View",
            query="SELECT 1",
            graph=fake_graph(),
        )

        await view_storage.create_or_replace_view(view)

        # Verify view was created
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT slug, title, query, folder_uid, position FROM views WHERE slug = $1",
            "test-view",
        )
        assert row is not None
        assert row["slug"] == "test-view"
        assert row["title"] == "Test View"
        assert row["query"] == "SELECT 1"
        assert row["folder_uid"] is None
        assert row["position"] == 0

    async def test_create_view_with_folder(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder
        await purged_psql_tenant_conn.execute(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2)",
            "test-folder",
            "Test Folder",
        )

        view = View(
            id="test-view",
            title="Test View",
            query="SELECT 1",
            folder_id="test-folder",
        )

        await view_storage.create_or_replace_view(view)

        # Verify view was created with correct folder_uid
        row = await purged_psql_tenant_conn.fetchrow(
            """
            SELECT v.slug, v.title, v.folder_uid, f.slug as folder_slug
            FROM views v
            JOIN view_folders f ON v.folder_uid = f.uid
            WHERE v.slug = $1
            """,
            "test-view",
        )
        assert row is not None
        assert row["folder_slug"] == "test-folder"

    async def test_create_view_with_nonexistent_folder(
        self,
        view_storage: PsqlViewStorage,
    ):
        view = View(
            id="test-view",
            title="Test View",
            query="SELECT 1",
            folder_id="nonexistent-folder",
        )

        with pytest.raises(ObjectNotFoundError):
            await view_storage.create_or_replace_view(view)

    async def test_create_view_generates_id_if_missing(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        view = View(id="", title="Test View", query="SELECT 1")

        await view_storage.create_or_replace_view(view)

        # Verify view was created with generated ID
        rows = await purged_psql_tenant_conn.fetch("SELECT slug FROM views WHERE title = $1", "Test View")
        assert len(rows) == 1
        assert rows[0]["slug"] != ""

    async def test_create_view_sets_position_automatically(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder with existing view
        folder_uid = await purged_psql_tenant_conn.fetchval(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2) RETURNING uid",
            "test-folder",
            "Test Folder",
        )
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, folder_uid, position) VALUES ($1, $2, $3, $4, $5)",
            "existing-view",
            "Existing View",
            "SELECT 0",
            folder_uid,
            0,
        )

        view = View(
            id="new-view",
            title="New View",
            query="SELECT 1",
            folder_id="test-folder",
        )

        await view_storage.create_or_replace_view(view)

        # Verify new view has position 1
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT position FROM views WHERE slug = $1",
            "new-view",
        )
        assert row is not None
        assert row["position"] == 1

    async def test_replace_existing_view(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder and view
        folder_uid = await purged_psql_tenant_conn.fetchval(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2) RETURNING uid",
            "test-folder",
            "Test Folder",
        )
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, folder_uid) VALUES ($1, $2, $3, $4)",
            "test-view",
            "Original Title",
            "SELECT 0",
            folder_uid,
        )

        view = View(
            id="test-view",
            title="Updated Title",
            query="SELECT 1",
            folder_id="test-folder",
        )

        await view_storage.create_or_replace_view(view)

        # Verify view was updated
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT title, query FROM views WHERE slug = $1",
            "test-view",
        )
        assert row is not None
        assert row["title"] == "Updated Title"
        assert row["query"] == "SELECT 1"

    async def test_folder_and_title_not_updated_if_falsy(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder and view
        folder_uid = await purged_psql_tenant_conn.fetchval(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2) RETURNING uid",
            "test-folder",
            "Test Folder",
        )
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, folder_uid) VALUES ($1, $2, $3, $4)",
            "test-view",
            "Original Title",
            "SELECT 0",
            folder_uid,
        )

        view = View(
            id="test-view",
            query="SELECT 1",
        )

        await view_storage.create_or_replace_view(view)

        # Verify view was updated
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT title, query, folder_uid FROM views WHERE slug = $1",
            "test-view",
        )
        assert row is not None
        assert row["title"] == "Original Title"
        assert row["folder_uid"] == folder_uid
        assert row["query"] == "SELECT 1"


class TestRetrieveView:
    async def test_retrieve_view_without_folder(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test view without folder
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, graph_type, graph) VALUES ($1, $2, $3, $4, $5)",
            "test-view",
            "Test View",
            "SELECT 1",
            "line",
            '{"x": {"field": "date"}, "y": [{"field": "count"}]}',
        )

        view = await view_storage.retrieve_view("test-view")

        assert view.id == "test-view"
        assert view.title == "Test View"
        assert view.query == "SELECT 1"
        assert view.folder_id is None
        assert view.graph is not None
        assert view.graph.type == "line"

    async def test_retrieve_view_with_folder(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder and view
        folder_uid = await purged_psql_tenant_conn.fetchval(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2) RETURNING uid",
            "test-folder",
            "Test Folder",
        )
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, folder_uid) VALUES ($1, $2, $3, $4)",
            "test-view",
            "Test View",
            "SELECT 1",
            folder_uid,
        )

        view = await view_storage.retrieve_view("test-view")

        assert view.id == "test-view"
        assert view.title == "Test View"
        assert view.folder_id == "test-folder"

    async def test_retrieve_view_nonexistent(
        self,
        view_storage: PsqlViewStorage,
    ):
        with pytest.raises(ObjectNotFoundError):
            await view_storage.retrieve_view("nonexistent-view")

    async def test_retrieve_view_deleted(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert deleted view
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, deleted_at) VALUES ($1, $2, $3, CURRENT_TIMESTAMP)",
            "deleted-view",
            "Deleted View",
            "SELECT 1",
        )

        with pytest.raises(ObjectNotFoundError):
            await view_storage.retrieve_view("deleted-view")


class TestUpdateView:
    async def test_update_view_title_and_query(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test view
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query) VALUES ($1, $2, $3)",
            "test-view",
            "Original Title",
            "SELECT 0",
        )

        await view_storage.update_view(
            "test-view",
            title="Updated Title",
            query="SELECT 1",
            graph=None,
            folder_id=None,
            position=None,
        )

        # Verify view was updated
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT title, query FROM views WHERE slug = $1",
            "test-view",
        )
        assert row is not None
        assert row["title"] == "Updated Title"
        assert row["query"] == "SELECT 1"

    async def test_update_view_graph(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test view
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query) VALUES ($1, $2, $3)",
            "test-view",
            "Test View",
            "SELECT 1",
        )

        graph = Graph(type="bar", attributes={"x": {"field": "date"}, "y": [{"field": "value"}]})

        await view_storage.update_view(
            "test-view",
            title=None,
            query=None,
            graph=graph,
            folder_id=None,
            position=None,
        )

        # Verify graph was updated
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT graph_type, graph FROM views WHERE slug = $1",
            "test-view",
        )
        assert row is not None
        assert row["graph_type"] == "bar"
        assert json.loads(row["graph"])["x"]["field"] == "date"

    async def test_update_view_folder(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test folder and view
        await purged_psql_tenant_conn.execute(
            "INSERT INTO view_folders (slug, name) VALUES ($1, $2)",
            "test-folder",
            "Test Folder",
        )
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query) VALUES ($1, $2, $3)",
            "test-view",
            "Test View",
            "SELECT 1",
        )

        await view_storage.update_view(
            "test-view",
            title=None,
            query=None,
            graph=None,
            folder_id="test-folder",
            position=None,
        )

        # Verify view was moved to folder
        row = await purged_psql_tenant_conn.fetchrow(
            """
            SELECT v.folder_uid, f.slug as folder_slug
            FROM views v
            JOIN view_folders f ON v.folder_uid = f.uid
            WHERE v.slug = $1
            """,
            "test-view",
        )
        assert row is not None
        assert row["folder_slug"] == "test-folder"

    async def test_update_view_with_nonexistent_folder(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test view
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query) VALUES ($1, $2, $3)",
            "test-view",
            "Test View",
            "SELECT 1",
        )

        with pytest.raises(ObjectNotFoundError):
            await view_storage.update_view(
                "test-view",
                title=None,
                query=None,
                graph=None,
                folder_id="nonexistent-folder",
                position=None,
            )

    async def test_update_view_folder_none(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        inserted_folder_uid = await _insert_view_folder(purged_psql_tenant_conn, "test-folder", "Test Folder")
        _ = await _insert_view(purged_psql_tenant_conn, "test-view", folder_uid=inserted_folder_uid)

        await view_storage.update_view(
            "test-view",
            title=None,
            query=None,
            graph=None,
            folder_id="",
            position=None,
        )

        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT folder_uid FROM views WHERE slug = $1",
            "test-view",
        )
        assert row is not None
        assert row["folder_uid"] is None

    async def test_update_view_position(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test view
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query, position) VALUES ($1, $2, $3, $4)",
            "test-view",
            "Test View",
            "SELECT 1",
            0,
        )

        await view_storage.update_view(
            "test-view",
            title=None,
            query=None,
            graph=None,
            folder_id=None,
            position=5,
        )

        # Verify position was updated
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT position FROM views WHERE slug = $1",
            "test-view",
        )
        assert row is not None
        assert row["position"] == 5


class TestDeleteView:
    async def test_delete_view(
        self,
        view_storage: PsqlViewStorage,
        purged_psql_tenant_conn,
    ):
        # Insert test view
        await purged_psql_tenant_conn.execute(
            "INSERT INTO views (slug, title, query) VALUES ($1, $2, $3)",
            "test-view",
            "Test View",
            "SELECT 1",
        )

        await view_storage.delete_view("test-view")

        # Verify view is marked as deleted
        row = await purged_psql_tenant_conn.fetchrow(
            "SELECT deleted_at FROM views WHERE slug = $1",
            "test-view",
        )
        assert row is not None
        assert row["deleted_at"] is not None

    async def test_delete_view_nonexistent(
        self,
        view_storage: PsqlViewStorage,
    ):
        # Should not raise an error for non-existent view
        await view_storage.delete_view("nonexistent-view")
