import os
from unittest.mock import patch

import pytest

# Create client for test user
from clickhouse_connect.driver import create_async_client
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import DatabaseError

from core.storage.clickhouse._utils import (
    build_tenant_uid_password,
    clone_client,
    sanitize_query,
    sanitize_readonly_privileges,
)
from core.utils import uuid


async def test_clone_client(clickhouse_client: AsyncClient):
    client = await clone_client(clickhouse_client, 2)
    assert client.client.database == "db_test"

    # Check that we can insert a completion with the original client

    # Create 2 rows, one with tenant_uid 1 and one with tenant_uid 2
    res = await clickhouse_client.insert(
        table="completions",
        column_names=["id", "tenant_uid"],
        data=[[uuid.uuid7(ms=lambda: 0, rand=lambda: 1), 1], [uuid.uuid7(ms=lambda: 0, rand=lambda: 2), 2]],
    )
    assert res.written_rows == 2

    res = await clickhouse_client.query("SELECT * FROM completions")
    assert len(res.result_rows) == 2, "sanity check"

    # Check that we cannot insert a completion with the readonly client
    with pytest.raises(DatabaseError, match="Not enough privileges"):
        _ = await client.insert(
            table="completions",
            column_names=["id"],
            data=[[uuid.uuid7()]],
        )
    # Also check that we cannot mutate
    with pytest.raises(DatabaseError, match="Not enough privileges"):
        _ = await client.command(
            "ALTER TABLE completions DELETE WHERE id = {uuid:UUID}",
            parameters={"uuid": uuid.uuid7()},
        )

    # Check that I can select, and I only get the rows for tenant_uid 2
    res = await client.query("SELECT tenant_uid, id FROM completions")
    assert len(res.result_rows) == 1
    assert res.result_rows[0][0] == 2
    assert res.result_rows[0][1] == uuid.uuid7(ms=lambda: 0, rand=lambda: 2)

    # Check that I can describe
    res = await client.query("DESCRIBE TABLE completions")
    assert res.result_rows


class TestSanitizeReadonlyPrivileges:
    async def test_fresh_user(self, clickhouse_client: AsyncClient):
        """Test sanitize_readonly_privileges with a fresh user that has no existing privileges."""
        tenant_uid = 100
        test_user = f"test_fresh_user_{tenant_uid}"
        database = clickhouse_client.client.database
        assert database is not None, "Database must be set for tests"
        password = build_tenant_uid_password(tenant_uid)

        # Create the user first
        await clickhouse_client.command(f"CREATE USER IF NOT EXISTS {test_user} IDENTIFIED BY '{password}'")

        # Setup test data in all tables that should be affected
        await clickhouse_client.insert(
            table="completions",
            column_names=["id", "tenant_uid"],
            data=[
                [uuid.uuid7(ms=lambda: 0, rand=lambda: 100), tenant_uid],  # Should be visible
                [uuid.uuid7(ms=lambda: 0, rand=lambda: 101), tenant_uid + 1],  # Should not be visible
            ],
        )

        await clickhouse_client.insert(
            table="annotations",
            column_names=["id", "tenant_uid"],
            data=[
                [str(uuid.uuid7(ms=lambda: 0, rand=lambda: 102)), tenant_uid],  # Should be visible
                [str(uuid.uuid7(ms=lambda: 0, rand=lambda: 103)), tenant_uid + 1],  # Should not be visible
            ],
        )

        await clickhouse_client.insert(
            table="experiments",
            column_names=["id", "tenant_uid"],
            data=[
                [str(uuid.uuid7(ms=lambda: 0, rand=lambda: 104)), tenant_uid],  # Should be visible
                [str(uuid.uuid7(ms=lambda: 0, rand=lambda: 105)), tenant_uid + 1],  # Should not be visible
            ],
        )

        # Apply readonly privileges
        await sanitize_readonly_privileges(clickhouse_client, tenant_uid, test_user)

        user_client = await create_async_client(
            dsn=clickhouse_client.client.uri,
            user=test_user,
            password=password,
            database=database,
        )

        try:
            # Test that user can only see their tenant's data in completions
            res = await user_client.query("SELECT tenant_uid FROM completions WHERE tenant_uid IN (100, 101)")
            assert len(res.result_rows) == 1
            assert res.result_rows[0][0] == tenant_uid

            # Test that user can only see their tenant's data in annotations
            res = await user_client.query("SELECT tenant_uid FROM annotations WHERE tenant_uid IN (100, 101)")
            assert len(res.result_rows) == 1
            assert res.result_rows[0][0] == tenant_uid

            # Test that user can only see their tenant's data in experiments
            res = await user_client.query("SELECT tenant_uid FROM experiments WHERE tenant_uid IN (100, 101)")
            assert len(res.result_rows) == 1
            assert res.result_rows[0][0] == tenant_uid

            # Test that user cannot perform write operations
            with pytest.raises(DatabaseError, match="Not enough privileges"):
                await user_client.insert(
                    table="completions",
                    column_names=["id", "tenant_uid"],
                    data=[[uuid.uuid7(), tenant_uid]],
                )
        finally:
            # Cleanup
            await user_client.close()
            await clickhouse_client.command(f"DROP USER IF EXISTS {test_user}")

    async def test_sanitize_readonly_privileges_partial_grants(self, clickhouse_client: AsyncClient):
        """Test sanitize_readonly_privileges with a user that already has partial grants."""
        tenant_uid = 200
        test_user = f"test_partial_user_{tenant_uid}"
        database = clickhouse_client.client.database
        assert database is not None, "Database must be set for tests"
        password = build_tenant_uid_password(tenant_uid)

        # Create the user and give them some partial privileges
        await clickhouse_client.command(f"CREATE USER IF NOT EXISTS {test_user} IDENTIFIED BY '{password}'")
        # Grant only SELECT on completions table initially (partial grant)
        await clickhouse_client.command(f"GRANT SELECT ON {database}.completions TO {test_user}")

        # Setup test data
        await clickhouse_client.insert(
            table="completions",
            column_names=["id", "tenant_uid"],
            data=[
                [uuid.uuid7(ms=lambda: 0, rand=lambda: 200), tenant_uid],
                [uuid.uuid7(ms=lambda: 0, rand=lambda: 201), tenant_uid + 1],
            ],
        )

        await clickhouse_client.insert(
            table="annotations",
            column_names=["id", "tenant_uid"],
            data=[
                [str(uuid.uuid7(ms=lambda: 0, rand=lambda: 202)), tenant_uid],
                [str(uuid.uuid7(ms=lambda: 0, rand=lambda: 203)), tenant_uid + 1],
            ],
        )

        await clickhouse_client.insert(
            table="experiments",
            column_names=["id", "tenant_uid"],
            data=[
                [str(uuid.uuid7(ms=lambda: 0, rand=lambda: 204)), tenant_uid],
                [str(uuid.uuid7(ms=lambda: 0, rand=lambda: 205)), tenant_uid + 1],
            ],
        )

        user_client_before = await create_async_client(
            dsn=clickhouse_client.client.uri,
            user=test_user,
            password=password,
            database=database,
        )

        # Verify user currently sees all data in completions (no row policy yet)
        res = await user_client_before.query("SELECT tenant_uid FROM completions WHERE tenant_uid IN (200, 201)")
        assert len(res.result_rows) == 2  # Should see both tenants' data

        # Verify user cannot access other tables yet (no grants)
        with pytest.raises(DatabaseError, match="Not enough privileges"):
            await user_client_before.query("SELECT tenant_uid FROM annotations")

        await user_client_before.close()

        # Now apply sanitize_readonly_privileges
        await sanitize_readonly_privileges(clickhouse_client, tenant_uid, test_user)

        # Create client for test user after sanitization
        user_client_after = await create_async_client(
            dsn=clickhouse_client.client.uri,
            user=test_user,
            password=password,
            database=database,
        )

        try:
            # Test that row policies are now properly applied - user should only see their tenant's data
            res = await user_client_after.query("SELECT tenant_uid FROM completions WHERE tenant_uid IN (200, 201)")
            assert len(res.result_rows) == 1
            assert res.result_rows[0][0] == tenant_uid

            # Test that user now has access to all tables with proper row policies
            res = await user_client_after.query("SELECT tenant_uid FROM annotations WHERE tenant_uid IN (200, 201)")
            assert len(res.result_rows) == 1
            assert res.result_rows[0][0] == tenant_uid

            res = await user_client_after.query("SELECT tenant_uid FROM experiments WHERE tenant_uid IN (200, 201)")
            assert len(res.result_rows) == 1
            assert res.result_rows[0][0] == tenant_uid

            # Test that user still cannot perform write operations
            with pytest.raises(DatabaseError, match="Not enough privileges"):
                await user_client_after.insert(
                    table="completions",
                    column_names=["id", "tenant_uid"],
                    data=[[uuid.uuid7(), tenant_uid]],
                )

        finally:
            # Cleanup
            await user_client_after.close()
            await clickhouse_client.command(f"DROP USER IF EXISTS {test_user}")


@patch.dict(os.environ, {"CLICKHOUSE_PASSWORD_SALT": "whatever"})
def test_build_tenant_uid_password():
    pwd = build_tenant_uid_password(1)
    # Clickhouse requires a password with at least 8 characters, a lowercase and uppercase letter and a special character
    assert len(pwd) > 8
    assert any(c.islower() for c in pwd)
    assert any(c.isupper() for c in pwd)
    assert any(c.isdigit() for c in pwd)

    assert "!" in pwd


class TestSanitizeQuery:
    # It's unfortunate but it looks like we cannot test the effect by using EXPLAIN PIPELINE
    # Best guess is that because of the low amount of data, both queries remain the same

    @pytest.mark.parametrize(
        ("input_query", "expected_output"),
        [
            # Basic case - simple ORDER BY created_at DESC
            (
                "SELECT * FROM completions WHERE tenant_uid = 9 ORDER BY created_at DESC LIMIT 10",
                "SELECT * FROM completions WHERE tenant_uid = 9 ORDER BY toDate(UUIDv7ToDateTime(id)) DESC, toUInt128(id) DESC LIMIT 10",
            ),
            # No ORDER BY clause - should remain unchanged
            (
                "SELECT * FROM completions WHERE tenant_uid = 9 LIMIT 10",
                "SELECT * FROM completions WHERE tenant_uid = 9 LIMIT 10",
            ),
            # ORDER BY different column - should remain unchanged
            (
                "SELECT * FROM completions ORDER BY agent_id DESC",
                "SELECT * FROM completions ORDER BY agent_id DESC",
            ),
            # ORDER BY with table alias
            (
                "SELECT * FROM completions c ORDER BY c.created_at DESC",
                "SELECT * FROM completions c ORDER BY c.created_at DESC",  # Only exact match is replaced
            ),
            # ORDER BY created_at DESC with window functions - note that sanitize_query replaces ALL occurrences
            (
                "SELECT *, ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY created_at DESC) as rn FROM completions ORDER BY created_at DESC",
                "SELECT *, ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY toDate(UUIDv7ToDateTime(id)) DESC, toUInt128(id) DESC) as rn FROM completions ORDER BY toDate(UUIDv7ToDateTime(id)) DESC, toUInt128(id) DESC",
            ),
        ],
    )
    def test_sanitize_query_parametrized(self, input_query: str, expected_output: str):
        """Test sanitize_query with various query patterns and edge cases."""
        result = sanitize_query(input_query)
        assert result == expected_output
