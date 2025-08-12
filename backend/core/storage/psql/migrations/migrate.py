from pathlib import Path

from asyncpg import Connection
from asyncpg.pool import PoolConnectionProxy


def _migration_id(file: Path) -> str:
    return file.stem


def _migration_files(last_migration_id: str | None) -> list[Path]:
    migrations = sorted(Path(__file__).parent.glob("*.sql"), key=_migration_id)
    # Make sure there are no duplicates
    file_names = {_migration_id(p) for p in migrations}
    if len(file_names) != len(migrations):
        raise ValueError("Duplicate migration files found")
    if last_migration_id:
        if last_migration_id not in file_names:
            raise ValueError(f"Last migration id {last_migration_id} not found in migration files")
        migrations = [p for p in migrations if _migration_id(p) > last_migration_id]
    return migrations


async def _migrate_file(conn: Connection | PoolConnectionProxy, file: Path):
    with open(file) as f:  # noqa: ASYNC230
        _ = await conn.execute(f.read())


async def _acquire_lock(conn: Connection | PoolConnectionProxy) -> str:
    _ = await conn.execute(
        "CREATE TABLE IF NOT EXISTS migrations (id SERIAL PRIMARY KEY, locked BOOLEAN NOT NULL DEFAULT FALSE, last_migration_id VARCHAR(64) NOT NULL DEFAULT '')",
    )

    row = await conn.fetchrow("""
    INSERT INTO migrations (id, locked, last_migration_id)
    VALUES (1, TRUE, '')
    ON CONFLICT (id) DO UPDATE
        SET locked = TRUE
        WHERE migrations.locked = FALSE
    RETURNING last_migration_id
""")
    if not row:
        raise ValueError("Failed to acquire lock")

    return row["last_migration_id"]


async def _release_lock(conn: Connection | PoolConnectionProxy, last_migration_id: str):
    _ = await conn.execute(
        "UPDATE migrations SET locked = FALSE, last_migration_id = $1 WHERE id = 1",
        last_migration_id,
    )


async def migrate(conn: Connection | PoolConnectionProxy):
    last_migration_id = await _acquire_lock(conn)
    migration_files = _migration_files(last_migration_id)

    for file in migration_files:
        await _migrate_file(conn, file)
        last_migration_id = _migration_id(file)

    await _release_lock(conn, last_migration_id)
