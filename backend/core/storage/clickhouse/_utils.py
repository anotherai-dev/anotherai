import os
from typing import Any

from clickhouse_connect.driver import create_async_client
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import DatabaseError
from pydantic import BaseModel

from core.utils.hash import hash_string


def data_and_columns(model: BaseModel, exclude_none: bool = True):
    dumped = model.model_dump(exclude_none=exclude_none)
    data: list[Any] = []
    columns: list[str] = []

    for key, value in dumped.items():
        data.append(value)
        columns.append(key)
    return data, columns


def build_tenant_uid_password(tenant_uid: int) -> str:
    # TODO: make that variable mandatory
    # We force a ! and uppercase and lowercase letter to match ch pwd requirements
    return f"Aa0!{hash_string(f'{os.environ["CLICKHOUSE_PASSWORD_SALT"]}-{tenant_uid}')}"


def build_tenant_uid_user(tenant_uid: int) -> str:
    return f"readonly_{tenant_uid}"


async def sanitize_readonly_privileges(client: AsyncClient, tenant_uid: int, user: str | None):
    if not client.client.database:
        raise ValueError("Client has no database")
    if not user:
        user = build_tenant_uid_user(tenant_uid)
    database = client.client.database
    tables = ["completions", "annotations", "experiments", "inputs"]
    for table in tables:
        _ = await client.command(
            f"CREATE ROW POLICY OR REPLACE tenant_{tenant_uid}_{table}_readonly ON {database}.{table} USING tenant_uid = {tenant_uid} TO {user}",
        )
        _ = await client.command(f"GRANT SELECT ON {database}.{table} TO {user}")


async def _create_readonly_user(
    client: AsyncClient,
    tenant_uid: int,
    user: str,
    password: str,
    database: str,
) -> AsyncClient:
    _ = await client.command(f"CREATE USER IF NOT EXISTS {user}  IDENTIFIED BY '{password}'")

    await sanitize_readonly_privileges(client, tenant_uid, user)
    return await create_async_client(
        dsn=client.client.uri,
        user=user,
        password=password,
        database=database,
    )


async def clone_client(client: AsyncClient, tenant_uid: int) -> AsyncClient:
    if not client.client.database:
        raise ValueError("Client has no database")
    user = build_tenant_uid_user(tenant_uid)
    password = build_tenant_uid_password(tenant_uid)
    try:
        return await create_async_client(
            dsn=client.client.uri,
            user=user,
            password=password,
            database=client.client.database,
        )
    except DatabaseError as e:
        if "Code: 516" in str(e):  # User does not exist or does not have necessary permissions
            return await _create_readonly_user(client, tenant_uid, user, password, client.client.database)

        raise e
