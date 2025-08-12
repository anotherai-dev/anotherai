import asyncpg
import pytest
from clickhouse_connect.driver.asyncclient import AsyncClient as CHAsyncClient
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from openai import AsyncOpenAI

from core.domain.models.models import Model
from core.domain.models.providers import Provider
from tests.asgi_transport import patch_asgi_transport
from tests.pausable_memory_broker import PausableInMemoryBroker


# TODO: re-enable when we have actual events
@pytest.fixture
async def patched_broker():
    return None
    # with patch("taskiq.InMemoryBroker", new=PausableInMemoryBroker):
    #     from api.broker import broker

    # return broker


@pytest.fixture
async def test_app(
    request: pytest.FixtureRequest,
    purged_psql: asyncpg.Pool,
    purged_clickhouse: CHAsyncClient,
    patched_broker: PausableInMemoryBroker,
    # Making sure the blob storage is created
    test_blob_storage: None,
):
    # Making sure the call is patched before applying all imports
    from protocol.api.api_server import api

    # making sure dependency overrides are cleared
    api.dependency_overrides = {}

    # Manually trigger the lifespan events since ASGITransport doesn't do it automatically
    async with api.router.lifespan_context(api), patch_asgi_transport():  # required for streaming
        yield api


@pytest.fixture
async def openai_client(test_app: FastAPI):
    transport = ASGITransport(app=test_app)
    headers: dict[str, str] = {}
    # if not request.node.get_closest_marker("unauthenticated"):  # type: ignore
    #     headers["Authorization"] = f"Bearer {_TEST_JWT}"

    api_client = AsyncClient(
        transport=transport,
        base_url="http://0.0.0.0",
        headers=headers,
    )
    return AsyncOpenAI(http_client=api_client, api_key="").with_options(
        # Disable retries
        max_retries=0,
    )


MODEL_PROVIDERS = [
    (Provider.OPEN_AI, Model.GPT_41_MINI_LATEST),
    (Provider.ANTHROPIC, Model.CLAUDE_3_5_SONNET_LATEST),
    (Provider.GOOGLE, Model.GEMINI_2_5_FLASH),
    (Provider.GOOGLE_GEMINI, Model.GEMINI_2_5_FLASH),
    (Provider.GROQ, Model.LLAMA_4_MAVERICK_FAST),
    (Provider.FIREWORKS, Model.DEEPSEEK_V3_0324),
    (Provider.X_AI, Model.GROK_3_MINI_BETA),
    (Provider.MISTRAL_AI, Model.MISTRAL_MEDIUM_2505),
]
