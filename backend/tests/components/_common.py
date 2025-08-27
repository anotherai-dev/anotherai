from typing import Any

from fastmcp import Client as MCPClient
from httpx import AsyncClient, HTTPStatusError, Response
from openai import AsyncOpenAI
from pytest_httpx import HTTPXMock

from core.domain.models.providers import Provider
from core.utils.background import wait_for_background_tasks
from tests.pausable_memory_broker import PausableInMemoryBroker
from tests.utils import fixtures_json


def openai_endpoint():
    return "https://api.openai.com/v1/chat/completions"


def anthropic_endpoint():
    return "https://api.anthropic.com/v1/messages"


def provider_matchers(provider: str, model: str) -> dict[str, Any]:
    match provider:
        case Provider.OPEN_AI:
            return {"url": openai_endpoint()}
        case Provider.ANTHROPIC:
            return {"url": anthropic_endpoint()}
        case _:
            raise ValueError(f"Unknown provider: {provider}")


class IntegrationTestClient:
    def __init__(self, client: AsyncClient, mcp: MCPClient[Any], broker: PausableInMemoryBroker, httpx_mock: HTTPXMock):
        self.client = client
        self.mcp = mcp
        self.broker = broker
        self.httpx_mock = httpx_mock

    async def wait_for_background(self):
        await wait_for_background_tasks()

    def openai_client(self):
        return AsyncOpenAI(http_client=self.client, api_key="").with_options(
            # Disable retries
            max_retries=0,
        )

    def mock_provider_call(
        self,
        provider: str,
        model: str,
        fixture_name: str,
        status_code: int = 200,
        is_reusable: bool = False,
        **kwargs: Any,
    ):
        matchers = provider_matchers(provider, model)
        self.httpx_mock.add_response(
            status_code=status_code,
            json=fixtures_json(fixture_name),
            **matchers,
            is_reusable=is_reusable,
            **kwargs,
        )

    def get_provider_requests(self, provider: str, model: str):
        matchers = provider_matchers(provider, model)
        reqs = self.httpx_mock.get_requests(**matchers)
        return reqs

    @classmethod
    def result_or_raise(cls, res: Response) -> Any:
        try:
            _ = res.raise_for_status()
        except HTTPStatusError as e:
            print(e.response.text)  # noqa: T201
            raise e

        if res.text:
            return res.json()
        return None

    async def get(self, url: str, **kwargs: Any) -> dict[str, Any]:
        return self.result_or_raise(await self.client.get(url, **kwargs))

    async def post(self, url: str, json: Any = None, **kwargs: Any) -> dict[str, Any]:
        return self.result_or_raise(await self.client.post(url, json=json, **kwargs))

    async def patch(self, url: str, json: Any, **kwargs: Any) -> dict[str, Any]:
        return self.result_or_raise(await self.client.patch(url, json=json, **kwargs))

    async def put(self, url: str, json: Any, **kwargs: Any) -> dict[str, Any]:
        return self.result_or_raise(await self.client.put(url, json=json, **kwargs))

    async def delete(self, url: str, **kwargs: Any) -> dict[str, Any]:
        return self.result_or_raise(await self.client.delete(url, **kwargs))

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        res = await self.mcp.call_tool(tool_name, arguments)
        return res.structured_content
