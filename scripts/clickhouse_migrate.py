import asyncio

import typer
from _common import EnvName, EnvNameOption, get_clickhouse_client
from dotenv import load_dotenv

from core.storage.clickhouse.migrations.migrate import migrate


async def _main(env_name: EnvName):
    # TODO: add dry run
    async with get_clickhouse_client(env_name) as client:
        await migrate(client)


if __name__ == "__main__":
    _ = load_dotenv(override=True)

    def wrapper(env: EnvNameOption = EnvName.LOCAL):
        asyncio.run(_main(env))

    typer.run(wrapper)
