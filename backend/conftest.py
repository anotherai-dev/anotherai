import contextlib
import os
import re
from unittest.mock import Mock, patch

import asyncpg
import pytest
from clickhouse_connect.driver.asyncclient import AsyncClient
from freezegun.api import freeze_time
from structlog.testing import capture_logs


@pytest.fixture(scope="session", autouse=True)
def setup_provider_keys():
    with patch.dict(
        os.environ,
        {
            "AWS_BEDROCK_MODEL_REGION_MAP": "{}",
            "AWS_BEDROCK_API_KEY": "secret",
            "OPENAI_API_KEY": "sk-proj-123",
            "GROQ_API_KEY": "gsk-proj-123",
            "AZURE_OPENAI_CONFIG": '{"deployments": {"eastus": { "url": "https://workflowai-azure-oai-staging-eastus.openai.azure.com/openai/deployments/", "api_key": "sk-proj-123", "models": ["gpt-4o-2024-11-20", "gpt-4o-mini-2024-07-18"]}}, "default_region": "eastus"}',
            "GOOGLE_VERTEX_AI_PROJECT_ID": "worfklowai",
            "GOOGLE_VERTEX_AI_LOCATION": "us-central1",
            "GOOGLE_VERTEX_AI_CREDENTIALS": '{"type":"service_account","project_id":"worfklowai"}',
            "GEMINI_API_KEY": "sk-proj-123",
            "FIREWORKS_API_KEY": "sk-proj-123",
            "FIREWORKS_API_URL": "https://api.fireworks.ai/inference/v1/chat/completions",
            "MISTRAL_API_KEY": "sk-proj-123",
            "ANTHROPIC_API_KEY": "sk-proj-1234",
            "FIRECRAWL_API_KEY": "firecrawl-api-key",
            "SCRAPINGBEE_API_KEY": "scrapingbee-api-key",
            "LOOPS_API_KEY": "loops-api-key",
            "XAI_API_KEY": "xai-123",
            "AMPLITUDE_API_KEY": "test_api_key",
            "AMPLITUDE_URL": "https://amplitude-mock",
            "BETTER_STACK_API_KEY": "test_bs_api_key",
            "SERPER_API_KEY": "serper-api-key",
            "PERPLEXITY_API_KEY": "perplexity-api-key",
            "ENRICH_SO_API_KEY": "enrich-so-api-key",
        },
    ):
        yield


@pytest.fixture(scope="session")
async def clickhouse_client():
    from clickhouse_connect.driver import create_async_client  # pyright: ignore[reportUnknownVariableType]
    from clickhouse_connect.driver.exceptions import DatabaseError

    dsn = os.getenv("CLICKHOUSE_DSN_TEST", "clickhouse://default:admin@localhost:8123/db_test")

    if "localhost" not in dsn:
        raise ValueError("Only local testing is supported")
    splits = dsn.split("/")
    db_name = splits[-1]
    rest = "/".join(splits[:-1])
    client = await create_async_client(dsn=rest)

    try:
        _ = await client.command(f"CREATE DATABASE {db_name};")  # pyright: ignore[reportUnknownMemberType]
    except DatabaseError as e:
        if f"Database {db_name} already exists" not in str(e):
            raise e
    await client.close()

    client = await create_async_client(dsn=dsn)
    # Drop all test tables
    for table in ["completions", "annotations", "experiments", "migrations"]:
        _ = await client.command(f"DROP TABLE IF EXISTS {table}")  # pyright: ignore[reportUnknownMemberType]

    # Drop all users except default
    users = await client.query("SELECT name FROM system.users")
    for user in users.result_rows:
        if user[0] != "default":
            _ = await client.command(f"DROP USER {user[0]}")  # pyright: ignore[reportUnknownMemberType]

    # Drop all row policies
    policies = await client.query("SELECT name FROM system.row_policies")
    for policy in policies.result_rows:
        _ = await client.command(f"DROP ROW POLICY {policy[0]}")  # pyright: ignore[reportUnknownMemberType]

    # Apply ClickHouse migrations in order
    from core.storage.clickhouse.migrations.migrate import migrate

    await migrate(client)

    with patch.dict(os.environ, {"CLICKHOUSE_PASSWORD_SALT": "test", "CLICKHOUSE_DSN": dsn}):
        yield client
    await client.close()


@pytest.fixture
async def purged_clickhouse(clickhouse_client: AsyncClient):
    _ = await clickhouse_client.command("TRUNCATE TABLE completions")  # pyright: ignore [reportUnknownMemberType]
    _ = await clickhouse_client.command("TRUNCATE TABLE annotations")  # pyright: ignore [reportUnknownMemberType]
    _ = await clickhouse_client.command("TRUNCATE TABLE experiments")  # pyright: ignore [reportUnknownMemberType]


@pytest.fixture(scope="session")
def admin_psql_dsn():
    dsn = os.getenv("PSQL_DSN_TEST", "postgresql://default:admin@localhost:5432/db_test")
    if "localhost" not in dsn:
        raise ValueError("Only local testing is supported")
    with patch.dict(os.environ, {"PSQL_DSN": dsn}):
        yield dsn


@pytest.fixture(scope="session")
async def migrated_database(admin_psql_dsn: str):
    import asyncpg

    from core.storage.psql.migrations.migrate import migrate

    splits = admin_psql_dsn.split("/")
    db_name = splits[-1]
    rest = "/".join(splits[:-1])

    conn = await asyncpg.connect(dsn=rest)
    _ = await conn.execute(f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);")
    _ = await conn.execute(f"CREATE DATABASE {db_name};")

    # Drop the test user
    with contextlib.suppress(asyncpg.exceptions.UndefinedObjectError):
        _ = await conn.execute("REVOKE ALL PRIVILEGES ON SCHEMA public FROM test_role")
        _ = await conn.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM test_role")
        _ = await conn.execute("DROP ROLE IF EXISTS test_role")
    _ = await conn.execute("CREATE ROLE test_role WITH LOGIN PASSWORD 'test'")
    _ = await conn.execute("GRANT CONNECT ON DATABASE db_test TO test_role")

    conn = await asyncpg.connect(dsn=admin_psql_dsn)
    await migrate(conn)
    # Grant access to all tables in public schema to test_role
    _ = await conn.execute("GRANT USAGE ON SCHEMA public TO test_role")
    _ = await conn.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO test_role")
    await conn.close()

    val = re.sub(r"postgresql://(.*:.*)@", "postgresql://test_role:test@", admin_psql_dsn)
    # replace the user and password in the dsn
    with patch.dict(os.environ, {"PSQL_DSN": val}):
        yield val


@pytest.fixture
async def psql_pool(migrated_database: str):
    import asyncpg

    pool = await asyncpg.create_pool(dsn=migrated_database)

    yield pool
    await pool.close()


@pytest.fixture
async def purged_psql(psql_pool: asyncpg.Pool, admin_psql_dsn: str):
    # Truncate all tables
    conn = await asyncpg.connect(dsn=admin_psql_dsn)
    _ = await conn.execute("TRUNCATE TABLE migrations CASCADE")
    _ = await conn.execute("TRUNCATE TABLE tenants CASCADE")
    await conn.close()
    return psql_pool


_TEST_AZURE_BLOB_DSN_TEST = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
_TEST_AZURE_BLOB_CONTAINER = "test-container"


@pytest.fixture(scope="session")
async def test_blob_storage():
    from azure.core.pipeline.transport import AioHttpTransport
    from azure.storage.blob import PublicAccess
    from azure.storage.blob.aio import BlobServiceClient

    container_name = os.environ.get("AZURE_BLOB_CONTAINER_TEST", _TEST_AZURE_BLOB_CONTAINER)
    connection_string = os.environ.get("AZURE_BLOB_DSN_TEST", _TEST_AZURE_BLOB_DSN_TEST)

    with patch.dict(
        os.environ,
        {
            "AZURE_BLOB_CONTAINER": container_name,
            "AZURE_BLOB_DSN": connection_string,
        },
    ):
        clt = BlobServiceClient.from_connection_string(
            os.environ["AZURE_BLOB_DSN"],
            transport=AioHttpTransport(
                connection_timeout=300.0,
                read_timeout=300.0,
                retries=3,
                maximum_valid_request_size=500 * 1024 * 1024,
            ),
        )

        try:
            # Check if the container exists
            container_clt = clt.get_container_client(container_name)
            _ = await container_clt.get_container_properties()
        except Exception:  # noqa: BLE001
            # Creating the container dynamically since it will not exist in the test environment
            container_clt = await clt.create_container(container_name)

        await container_clt.set_container_access_policy(  # type: ignore
            signed_identifiers={},
            public_access=PublicAccess.BLOB,
        )
        await clt.close()
        yield container_name, connection_string


@pytest.fixture
def frozen_time():
    with freeze_time("2024-08-12T00:00:00Z") as frozen_time:
        yield frozen_time


@pytest.fixture
def mock_experiment_storage():
    from core.storage.experiment_storage import ExperimentStorage

    return Mock(spec=ExperimentStorage)


@pytest.fixture
def mock_completion_storage():
    from core.storage.completion_storage import CompletionStorage

    return Mock(spec=CompletionStorage)


@pytest.fixture
def mock_agent_storage():
    from core.storage.agent_storage import AgentStorage

    return Mock(spec=AgentStorage)


@pytest.fixture
def mock_event_router():
    from core.domain.events import EventRouter

    return Mock(spec=EventRouter)


@pytest.fixture
def mock_deployment_storage():
    from core.storage.deployment_storage import DeploymentStorage

    return Mock(spec=DeploymentStorage)


@pytest.fixture
def mock_annotation_storage():
    from core.storage.annotation_storage import AnnotationStorage

    return Mock(spec=AnnotationStorage)


@pytest.fixture
def mock_view_storage():
    from core.storage.view_storage import ViewStorage

    return Mock(spec=ViewStorage)


@pytest.fixture
def mock_user_storage():
    from core.storage.user_storage import UserStorage

    return Mock(spec=UserStorage)


@pytest.fixture
def mock_tenant_storage():
    from core.storage.tenant_storage import TenantStorage

    return Mock(spec=TenantStorage)


@pytest.fixture
def mock_storage_builder(
    mock_agent_storage: Mock,
    mock_completion_storage: Mock,
    mock_experiment_storage: Mock,
    mock_annotation_storage: Mock,
    mock_view_storage: Mock,
    mock_deployment_storage: Mock,
    mock_user_storage: Mock,
    mock_tenant_storage: Mock,
    mock_event_router: Mock,
):
    from core.storage.storage_builder import StorageBuilder

    builder = Mock(spec=StorageBuilder)
    builder.agents.return_value = mock_agent_storage
    builder.completions.return_value = mock_completion_storage
    builder.experiments.return_value = mock_experiment_storage
    builder.annotations.return_value = mock_annotation_storage
    builder.views.return_value = mock_view_storage
    builder.deployments.return_value = mock_deployment_storage
    builder.users.return_value = mock_user_storage
    builder.tenants.return_value = mock_tenant_storage

    return builder


@pytest.fixture
def mock_provider_factory():
    from core.providers.factory.abstract_provider_factory import AbstractProviderFactory

    return Mock(spec=AbstractProviderFactory)


@pytest.fixture
def cap_structlogs():
    with capture_logs() as cap_logs:
        yield cap_logs
