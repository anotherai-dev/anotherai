from typing import Any
from unittest import mock

from tests.components._common import IntegrationTestClient


async def test_list_tools(test_api_client: IntegrationTestClient):
    res = await test_api_client.mcp.list_tools()
    assert res
    playground = next(tool for tool in res if tool.name == "playground")
    properties: dict[str, Any] = playground.inputSchema.get("properties", {})

    inputs: dict[str, Any] = properties.get("inputs", {})
    assert inputs["anyOf"] == [
        {
            "type": "array",
            "items": mock.ANY,
        },
        {
            "type": "null",
        },
        {
            "type": "string",
        },
    ]

    # Call again, make sure it was not modified
    res2 = await test_api_client.mcp.list_tools()
    playground2 = next(tool for tool in res2 if tool.name == "playground")

    inputs2: dict[str, Any] = playground2.inputSchema.get("properties", {}).get("inputs", {})
    assert inputs2["anyOf"] == [
        {
            "type": "array",
            "items": mock.ANY,
        },
        {
            "type": "null",
        },
        {
            "type": "string",
        },
    ]
