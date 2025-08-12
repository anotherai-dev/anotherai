import os
from contextlib import asynccontextmanager
from enum import StrEnum
from typing import Annotated

import asyncpg
import typer
from clickhouse_connect.driver import create_async_client
from rich import print  # noqa: A004

PSQL_DSN_VAR = "PSQL_DSN"
CLICKHOUSE_DSN_VAR = "CLICKHOUSE_DSN"
FILE_STORAGE_DSN_VAR = "FILE_STORAGE_DSN"
FILE_STORAGE_CONTAINER_NAME_VAR = "FILE_STORAGE_CONTAINER_NAME"

LOCAL_PREFIX = "LOCAL_"
STAGING_PREFIX = "STAGING_"
PROD_PREFIX = "PROD_"


class EnvName(StrEnum):
    STAGING = "staging"
    PROD = "prod"
    LOCAL = "local"


EnvNameOption = Annotated[EnvName, typer.Option()]


def prefixed_var(env_name: EnvName, var: str):
    if env_name == "prod":
        return os.environ[f"{PROD_PREFIX}{var}"]
    if env_name == "staging":
        return os.environ[f"{STAGING_PREFIX}{var}"]
    if env_name == "local":
        return os.environ.get(f"{LOCAL_PREFIX}{var}", os.environ[var])
    raise ValueError(f"Invalid env name: {env_name}")


@asynccontextmanager
async def get_psql_conn(env_name: EnvName):
    dsn = prefixed_var(env_name, var=PSQL_DSN_VAR)
    conn = await asyncpg.connect(dsn)
    yield conn
    await conn.close()


@asynccontextmanager
async def get_clickhouse_client(env_name: EnvName):
    dsn = prefixed_var(env_name, var=CLICKHOUSE_DSN_VAR)
    client = await create_async_client(dsn=dsn)
    yield client
    await client.close()


def is_true(var: str | None) -> bool:
    return var in {"t", "true", "1", "y", "yes", "Y", "YES", "TRUE", "T"}


def get_current_branch() -> str:
    return os.popen("git branch --show-current").read().strip()  # noqa: S605, S607


def is_prod_branch(branch: str) -> bool:
    return branch in {"main", "master"} or branch.startswith(("release/", "hotfix/"))


def raise_if_not_prod_branch():
    branch = get_current_branch()
    if not is_prod_branch(branch):
        raise ValueError(f"Current branch {branch} is not a prod branch")


def wait_for_truthy_input(prompt: str):
    i = input(f"{prompt}? [Y/n]")
    if i and not is_true(i):
        print("Exiting")
        os.abort()
