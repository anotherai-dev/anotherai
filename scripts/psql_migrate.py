import asyncio

import typer
from _common import EnvName, EnvNameOption, get_psql_conn
from dotenv import load_dotenv

from core.storage.psql.migrations.migrate import migrate


async def _main(env_name: EnvName):
    # TODO: add dry run

    async with get_psql_conn(env_name) as conn:
        await migrate(conn)


if __name__ == "__main__":
    _ = load_dotenv(override=True)

    def wrapper(env: EnvNameOption = EnvName.LOCAL):
        asyncio.run(_main(env))

    typer.run(wrapper)
