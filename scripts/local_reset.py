import asyncio
import os

import asyncpg
from clickhouse_connect.driver import create_async_client  # pyright: ignore[reportUnknownVariableType]
from dotenv import load_dotenv  # pyright: ignore[reportUnknownVariableType]


async def _reset_psql():
    dsn = os.environ["PSQL_DSN"]
    if "localhost" not in dsn:
        raise ValueError("Only local testing is supported")

    splits = dsn.split("/")
    db_name = splits[-1]
    rest = "/".join(splits[:-1])

    conn = await asyncpg.connect(dsn=rest)
    await conn.execute(f"DROP DATABASE IF EXISTS {db_name};")
    await conn.execute(f"CREATE DATABASE {db_name};")
    await conn.close()


async def _reset_clickhouse():
    dsn = os.environ["CLICKHOUSE_DSN"]
    if "localhost" not in dsn:
        raise ValueError("Only local testing is supported")

    splits = dsn.split("/")
    db_name = splits[-1]
    rest = "/".join(splits[:-1])

    client = await create_async_client(dsn=rest)
    await client.command(f"DROP DATABASE IF EXISTS {db_name};")  # pyright: ignore[reportUnknownMemberType]
    await client.command(f"CREATE DATABASE {db_name};")  # pyright: ignore[reportUnknownMemberType]
    await client.close()


async def main():
    await _reset_psql()
    await _reset_clickhouse()


if __name__ == "__main__":
    _ = load_dotenv(override=True)
    asyncio.run(main())
