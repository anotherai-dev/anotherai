from datetime import UTC, datetime
from pathlib import Path

from clickhouse_connect.driver.asyncclient import AsyncClient


def _migration_id(file: Path) -> str:
    return file.stem


def _read_sql_commands(file: Path) -> list[str]:
    """Splits a file into a list of sql commands"""
    setup_sql_commands = file.read_text().splitlines()
    lines_per_command: list[list[str]] = [[]]
    # Remove all lines that start with --
    for line in setup_sql_commands:
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        lines_per_command[-1].append(stripped)
        if stripped.endswith(";"):
            lines_per_command.append([])

    return ["\n".join(lines) for lines in lines_per_command if lines]


def _migration_files(existing_migrations: list[str]) -> list[Path]:
    migrations = sorted(Path(__file__).parent.glob("*.sql"), key=_migration_id)
    # Make sure there are no duplicates
    file_names = {_migration_id(p) for p in migrations}
    if len(file_names) != len(migrations):
        raise ValueError("Duplicate migration files found")

    if existing_migrations != [_migration_id(p) for p in migrations][: len(existing_migrations)]:
        raise ValueError("Migration discrepancy detected")

    return migrations[len(existing_migrations) :]


async def _migrate_file(client: AsyncClient, file: Path):
    commands = _read_sql_commands(file)
    for cmd in commands:
        _ = await client.command(cmd)  # pyright: ignore[reportUnknownMemberType]


async def _existing_migrations(client: AsyncClient) -> list[str]:
    result = await client.query("SELECT migration_id FROM migrations ORDER BY migration_id ASC")
    return [row[0] for row in result.result_rows]


async def migrate(client: AsyncClient):
    # Add a lock mechanism ? looks like having locks in clickhouse is a bit tricky
    # For now we should just be very careful to not run concurrent migrations
    _ = await client.command(
        "CREATE TABLE IF NOT EXISTS migrations (migration_id String, migrated_at DateTime) ENGINE = MergeTree ORDER BY migration_id",
    )
    existing_migrations = await _existing_migrations(client)
    migration_files = _migration_files(existing_migrations)

    for file in migration_files:
        await _migrate_file(client, file)
        await client.insert(
            "migrations",
            data=[[_migration_id(file), datetime.now(UTC)]],
            column_names=["migration_id", "migrated_at"],
            settings={"async_insert": 0},  # inserting in sync
        )
