import json
import os
from typing import Any

from fastmcp import Client as MCPClient
from httpx import AsyncClient, HTTPStatusError, Response
from openai import AsyncOpenAI
from pytest_httpx import HTTPXMock

from core.domain.models.providers import Provider
from core.utils.background import active_background_task_count, wait_for_background_tasks
from tests.pausable_memory_broker import PausableInMemoryBroker
from tests.utils import fixtures_json


def openai_endpoint():
    return "https://api.openai.com/v1/chat/completions"


def anthropic_endpoint():
    return "https://api.anthropic.com/v1/messages"


def groq_endpoint():
    return "https://api.groq.com/openai/v1/chat/completions"


def provider_matchers(provider: str, model: str) -> dict[str, Any]:
    match provider:
        case Provider.OPEN_AI:
            return {"url": openai_endpoint()}
        case Provider.ANTHROPIC:
            return {"url": anthropic_endpoint()}
        case Provider.GROQ:
            return {"url": groq_endpoint()}
        case _:
            raise ValueError(f"Unknown provider: {provider}")


class IntegrationTestClient:
    def __init__(self, client: AsyncClient, mcp: MCPClient[Any], broker: PausableInMemoryBroker, httpx_mock: HTTPXMock):
        self.client = client
        self.mcp = mcp
        self.broker = broker
        self.httpx_mock = httpx_mock

    async def wait_for_background(self, max_retries: int = 10):
        running: list[Any] = []
        for _ in range(max_retries):
            await wait_for_background_tasks()

            await self.broker.wait_all()
            # Retrying since some tasks could have created other tasks
            running = [task for task in self.broker._running_tasks if not task.done()]  # pyright: ignore [reportPrivateUsage]  # noqa: SLF001
            if not running and not active_background_task_count():
                return

        raise TimeoutError(
            f"Tasks did not complete {list(running)} or {active_background_task_count()} background tasks",
        )

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

    async def mock_internal_agent(self, content: str | dict[str, Any]):
        if isinstance(content, dict):
            content = json.dumps(content)

        self.httpx_mock.add_response(
            url=f"{os.environ['ANOTHERAI_API_URL']}/v1/chat/completions",
            json={
                "choices": [
                    {
                        "message": {
                            "content": content,
                        },
                    },
                ],
            },
        )
