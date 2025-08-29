import base64
import json
import os
from contextlib import asynccontextmanager
from typing import Any, cast
from unittest.mock import patch

import asyncpg
import jwt
import pytest
from clickhouse_connect.driver.asyncclient import AsyncClient as CHAsyncClient
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from fastapi import FastAPI
from fastmcp import Client, FastMCP
from httpx import ASGITransport, AsyncClient
from pytest_httpx import HTTPXMock
from starlette.requests import Request

from tests.asgi_transport import patch_asgi_transport
from tests.components._common import IntegrationTestClient
from tests.pausable_memory_broker import PausableInMemoryBroker


@pytest.fixture(scope="session")
def test_private_key() -> RSAPrivateKey:
    return cast(
        RSAPrivateKey,
        serialization.load_pem_private_key(
            b"""-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDE7dEWdUU2lP1A
MC6+GpMGZzhy0y57Ic/Ny/hGegnql7MQ1HOeuuyRO1O0PnNlykQBDOSb+fWqUmbE
Hi6vzghqV5Wpt3WSIkPnO7vRDcKVDqp/p3ddaBb8vfXsApeYihavnKC0chVeDb7R
8128CaHKar1yHCzdEDfrM+IRobIQomJNqyLEUf3jLGmed3ydhSnb305f5mfvrRxn
zn4Hp2m0r7vk25BmEHCXwO1IsyduTrXmjztCpQ7wizI29QcyuL/g9DgCd0exeWC6
dHHz/9JkFhsCYIytsjffXvK6YyyEg6sPlArqqfVn0hGOWyHiekRCGO0wRFa3waBj
XlsxEO9BAgMBAAECggEAdF5v6sx7jOh3yqFuTaoYbXU7dybx1ZNCX8MDQGpHR9hC
2VQhyo980cl0ChPJT0I580DyKnWHxRESZxvKzNp8QJLm/rZJhIQ5CgBTWRK/hCN5
fxuvvoOO6eU62C8j8+DNzRJKKLcthzmqJBiisEYk1B9FOZQKssstsBAlq/OX7Jlt
feDEAQ5zvaDEe7f6jAbHzLXBArV1ROhNXjZKcM2akBW0dngWfpgtjLWaJK1NS/K+
X5VCakEKglGjHxfZ6KM8dyB5KWOzWcG985XXxF2x1No5kvu7mp/7ZEKkOy2q/tOM
FK5zAWtgXS0Kf1OOdn4rwNHo2psZvBlnd1zJOdUQ0QKBgQD6So7okOujiAdKCpbK
xho/C65mRDvYQbS63UTdopgLu9OEWWvcNh7P9AdWM95O2v9ywjeSHd2YH35AsRAf
S1sody1AY+C5e1f1OeCe8rjxdJtWUgHAUlZAaIiANNBjZzIZJp0j+80GJwqbvbV9
ieWoN0CDIgKmiR7eoljKBsLCnQKBgQDJa62XHFwRjIBW1J+Pl9SNW+/0eRgdee+q
rnsABRO77x1g4NGktuj5O4f+VWYMt2bpfWm9d5j3427cKqvRk8onKPaAJPwL28Ju
RsVkowQ35C6bfC+cCg3q+BBOAdsP8rKtTvqXvduYF3LKQpipHJ0VGSVVsu2OQ1T5
tl05LVS79QKBgEybY3BFYwoziV+dLBg2WDQxxBhjDBodyk5jiT95E6aLv6rDn+LP
4dBudYxp5cIm/4bFcTLU101HXmI4j6G0c9tH1t7dcxvyZ7KUG28rBXZJ5X2fLhAK
Y4HlPNpYz+uM22WdTv2DhXY7nuCaSSF6goNhHerFDyCf2YX1FM4JEbV1AoGBAKlu
y8p2j7gvYXIpT8PBq4nx0YrsJm39Oa9xMISWwL/xZ9wrog6V0qp8+mvmuH5v9MDq
v30i0umLRqErv/b/BCkm2xx2gBMVnJuZKsj6HD1L1Cz1LTNsfcKvQz/rbbQfq1AA
ROpKSiPJbcVYegSfzj+GNJK/ffeTCjM4xXioekPVAoGARKi2xJMVKeXCh1jtWVtn
8wTM7PT8K28yAf8kknjnC3+lFLnwOUhkhH3XjfDEwYPXnAxm6zB99JNkQfDYyC+p
xFgaiRPYOTgpSMyTD1vY3yjJUgoNl1N8aw0yoLa3VS8TRiKo0yIEyDU96y/KQDN1
ayRIg49HYtsurtyfnan9wuc=
-----END PRIVATE KEY-----""",
            password=None,
            backend=default_backend(),
        ),
    )


@pytest.fixture(scope="session")
def test_jwk(test_private_key: RSAPrivateKey) -> dict[str, Any]:
    # build a JWK from the public version of the key
    public_key = test_private_key.public_key()

    def _b64url_uint(x: int) -> str:
        raw = x.to_bytes((x.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    nums = public_key.public_numbers()
    jwk = {
        "kty": "RSA",
        "n": _b64url_uint(nums.n),
        "e": _b64url_uint(nums.e),
        "alg": "RS256",
        "kid": "1",
    }
    return jwk


@pytest.fixture
def test_jwt(test_private_key: RSAPrivateKey) -> str:
    return jwt.encode(
        {"sub": "1234567890", "org_id": "org_123", "org_slug": "org-123"},
        test_private_key,
        algorithm="RS256",
        headers={"kid": "1"},
    )


@pytest.fixture(scope="session", autouse=True)
def setup_environment(test_jwk: dict[str, Any]):
    # TODO: this is likely executed after the database creation in the root conftest.py
    # Meaning that this will only work if the connection string here matches the one in the root conftest.py
    # which is not great
    clickhouse_test_connection_string = os.environ.get(
        "CLICKHOUSE_DSN_TEST_INT",
        "clickhouse://default:admin@localhost:8123/db_test",
    )
    psql_test_connection_string = os.environ.get(
        "PSQL_DSN_TEST_INT",
        "postgresql://default:admin@localhost:5432/db_test",
    )
    with patch.dict(
        os.environ,
        {
            "PSQL_DSN": psql_test_connection_string,
            "PSQL_DSN_TEST": psql_test_connection_string,
            "CLICKHOUSE_DSN_TEST": clickhouse_test_connection_string,
            "CLICKHOUSE_DSN": clickhouse_test_connection_string,
            "STORAGE_AES": "ruQBOB/yrSJYw+hozAGewJx5KAadHAMPnATttB2dmig=",
            "STORAGE_HMAC": "ATWcst2v/c/KEypN99ujwOySMzpwCqdaXvHLGDqBt+c=",
            "AWS_BEDROCK_API_KEY": "secret",
            "CLERK_WEBHOOKS_SECRET": "whsec_LCi7t70Dv3NryHc386aaOzjgDPl/Ta/D",
            "STRIPE_WEBHOOK_SECRET": "whsec_LCi7t70Dv3NryHc386aaOzjgDPl/Ta/D",
            "STRIPE_API_KEY": "sk-proj-123",
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
            "AZURE_BLOB_DSN": "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;",
            "AZURE_BLOB_CONTAINER": "workflowai-test-task-runs",
            "FIRECRAWL_API_KEY": "firecrawl-api-key",
            "SCRAPINGBEE_API_KEY": "scrapingbee-api-key",
            "SCRAPINGBEE_API_URL": "https://api.scrapingbee.com/scrape",
            "MODERATION_ENABLED": "false",
            "JOBS_BROKER_URL": "memory://",
            "CLERK_SECRET_KEY": "sk_test_123",
            "LOOPS_API_KEY": "loops-api-key",
            "PAYMENT_FAILURE_EMAIL_ID": "",
            "LOW_CREDITS_EMAIL_ID": "",
            "XAI_API_KEY": "xai-123",
            "AMPLITUDE_API_KEY": "test_api_key",
            "AMPLITUDE_URL": "https://amplitude-mock",
            "BETTER_STACK_API_KEY": "test_bs_api_key",
            "SERPER_API_KEY": "serper-api-key",
            "PERPLEXITY_API_KEY": "perplexity-api-key",
            "ENRICH_SO_API_KEY": "enrich-so-api-key",
            "CLICKHOUSE_PASSWORD_SALT": "test",
            "JWK": json.dumps(test_jwk, separators=(",", ":")),
        },
        clear=True,
    ):
        yield


# Depend on existing sessions to make sure they are created before the broker is started
@pytest.fixture(scope="session")
async def patched_broker(migrated_database: None, test_blob_storage: None, clickhouse_client: None):
    with patch("taskiq.InMemoryBroker", new=PausableInMemoryBroker):
        from protocol.worker.worker import broker

    await broker.startup()
    yield broker
    await broker.shutdown()


@pytest.fixture(scope="session", autouse=True)
def patched_google_auth():
    with patch(
        "core.providers.google.google_provider_auth.get_token",
        autospec=True,
        return_value="test_token",
    ) as mock_get_token:
        yield mock_get_token


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # We need to make sure the lifespan is only run once
    if getattr(app.state, "setup_done", None) is None:

        @asynccontextmanager
        async def mock_mcp_lifespan(app: FastAPI):
            # Overriding to avoid calling the FastMCP lifespan which creates issue
            # with the async loop
            yield

        with patch("protocol.api.api_server._mcp_lifespan", new=mock_mcp_lifespan):
            async with app.router.lifespan_context(app):
                app.state.setup_done = True
                yield app
    else:
        yield app


# Fixtures are added to make sure env vars are set correctly
@pytest.fixture(scope="session")
async def test_api_server(migrated_database: str, clickhouse_client: CHAsyncClient):
    # Making sure the call is patched before applying all imports

    from protocol.api._mcp import mcp
    from protocol.api.api_server import api

    # making sure dependency overrides are cleared
    api.dependency_overrides = {}
    async with _lifespan(api), patch_asgi_transport():  # required for streaming
        yield api, mcp


@pytest.fixture
async def test_api_client(
    request: pytest.FixtureRequest,
    purged_psql: asyncpg.Pool,
    psql_pool: asyncpg.Pool,
    purged_clickhouse: CHAsyncClient,
    httpx_mock: HTTPXMock,
    patched_broker: PausableInMemoryBroker,
    # Making sure the blob storage is created
    test_blob_storage: None,
    test_api_server: tuple[FastAPI, FastMCP[Any]],
    test_jwt: str,
):
    # Making sure the call is patched before applying all imports

    def _mock_get_http_request():
        return Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/mcp",
                "headers": [
                    (b"host", b"localhost:8000"),
                    (b"authorization", f"Bearer {test_jwt}".encode()),
                ],
            },
        )

    # Manually trigger the lifespan events since ASGITransport doesn't do it automatically

    headers: dict[str, str] = {
        "Authorization": f"Bearer {test_jwt}",
    }
    # if not request.node.get_closest_marker("unauthenticated"):  # type: ignore
    #     headers["Authorization"] = f"Bearer {_TEST_JWT}"

    transport = ASGITransport(app=test_api_server[0])

    api_client = AsyncClient(
        transport=transport,
        base_url="http://0.0.0.0",
        headers=headers,
    )

    with patch("protocol.api._mcp_utils.get_http_request", side_effect=_mock_get_http_request):
        async with Client(test_api_server[1]) as mcp_client:
            client = IntegrationTestClient(api_client, mcp_client, patched_broker, httpx_mock)
            yield client

    # Making sure all tasks are completed before exiting
    await client.wait_for_background()
