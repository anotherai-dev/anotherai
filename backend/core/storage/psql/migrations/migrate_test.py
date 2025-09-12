# pyright: reportPrivateUsage=false

import asyncpg
import pytest

from core.storage.psql.migrations.migrate import _migration_files

_EXCLUDED_TABLES = ("tenants", "api_keys", "migrations", "users")


async def test_migrate(admin_psql_dsn: str):
    splits = admin_psql_dsn.split("/")
    rest = "/".join(splits[:-1])
    test_migration_db_name = "test_migration_db"

    conn = await asyncpg.connect(dsn=f"{rest}")
    _ = await conn.execute(f"DROP DATABASE IF EXISTS {test_migration_db_name} WITH (FORCE);")
    _ = await conn.execute(f"CREATE DATABASE {test_migration_db_name};")

    migration_files = _migration_files(None)

    conn = await asyncpg.connect(dsn=f"{rest}/{test_migration_db_name}")

    for i, file in enumerate(migration_files):
        try:
            _ = await conn.execute(file.read_text())
        except Exception as e:  # noqa: BLE001
            pytest.fail(f"Migration {i} {file.stem} failed: {e}")

    # Additional checks for RLS, policies, default, and reference on tenant_uid
    # Dynamically get all user tables except tenants, api_keys, and migration/meta tables
    table_names = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    tables_to_check = [row["tablename"] for row in table_names if row["tablename"] not in _EXCLUDED_TABLES]

    async def _chect_table(table: str):
        rls = await conn.fetchval("SELECT relrowsecurity FROM pg_class WHERE relname = $1", table)
        assert rls is not None, f"{table} does not have RLS enabled"
        policy_qual = await conn.fetchval(
            "SELECT qual FROM pg_policies WHERE tablename = $1 AND policyname LIKE '%tenant_isolation_policy%'",
            table,
        )
        assert policy_qual == "(tenant_uid = (current_setting('app.tenant_uid'::text))::bigint)", (
            f"{table} does not have tenant isolation policy"
        )

        tenant_uid_default = await conn.fetchval(
            """
            SELECT column_default FROM information_schema.columns WHERE table_name = $1 AND column_name = 'tenant_uid'
            """,
            table,
        )
        assert tenant_uid_default == "(current_setting('app.tenant_uid'::text))::bigint", (
            f"{table} does not have default value for tenant_uid"
        )

        tenant_uid_reference = await conn.fetchrow(
            """
            SELECT tc.constraint_name FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            WHERE tc.table_name = $1 AND kcu.column_name = 'tenant_uid' AND tc.constraint_type = 'FOREIGN KEY'
            """,
            table,
        )
        assert tenant_uid_reference is not None, f"{table} does not have reference on tenant_uid"

    for table in tables_to_check:
        await _chect_table(table)

    await conn.close()
