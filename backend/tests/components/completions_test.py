from uuid import UUID

import pytest
from fastmcp.exceptions import ToolError
from httpx import HTTPStatusError

from core.utils.uuid import uuid7
from tests.components._common import IntegrationTestClient


async def test_import_completion(test_api_client: IntegrationTestClient):
    base_completion_payload = {
        "agent_id": "test-agent",
        "version": {
            "model": "gpt-4o-mini",
        },
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": "Hello, world!",
                },
            ],
        },
        "output": {
            "messages": [
                {
                    "role": "assistant",
                    "content": "Hello, world!",
                },
            ],
        },
        "cost_usd": 1.0,
        "duration_seconds": 1.0,
    }

    completion = await test_api_client.post("/v1/completions", json=base_completion_payload)
    assert completion["id"] is not None
    assert UUID(completion["id"]) is not None
    assert completion["url"] is not None

    # Check that a new agent was created
    agent = await test_api_client.get("/v1/agents")
    assert agent["items"]
    assert len(agent["items"]) == 1
    agent = agent["items"][0]
    assert agent["id"] == base_completion_payload["agent_id"]
    assert agent["uid"]

    # I can fetch the completion
    fetched_completion = await test_api_client.get(f"/v1/completions/{completion['id']}")
    assert fetched_completion["id"] == completion["id"]
    assert fetched_completion["cost_usd"] == 1.0
    assert fetched_completion["version"]["id"] is not None, "version id was not generated"
    assert fetched_completion["duration_seconds"] == 1.0

    # Now let's try to add a completion by specifying the id
    new_id = str(uuid7())
    completion = await test_api_client.post(
        "/v1/completions",
        json={
            "id": new_id,
            **base_completion_payload,
        },
    )
    assert completion["id"] == new_id
    assert completion["url"] is not None
    fetched_completion = await test_api_client.get(f"/v1/completions/{new_id}")
    assert fetched_completion["id"] == new_id

    # Now let's try to add a completion by specifying an invalid id
    with pytest.raises(HTTPStatusError):
        await test_api_client.post(
            "/v1/completions",
            {
                "id": "invalid-id",
                **base_completion_payload,
            },
        )

    # We should still have a single agent
    agent = await test_api_client.get("/v1/agents")
    assert agent["items"]
    assert len(agent["items"]) == 1
    agent = agent["items"][0]
    assert agent["id"] == base_completion_payload["agent_id"]
    assert agent["uid"]


async def test_query_completion_errors(test_api_client: IntegrationTestClient):
    with pytest.raises(HTTPStatusError) as e:
        await test_api_client.get("/v1/completions/query?query=SELECT * FROM whatnot")
    assert e.value.response.status_code == 400
    assert e.value.response.json()["error"]["message"].startswith("UNKNOWN_TABLE: ")

    # Same thing with the MCP
    with pytest.raises(ToolError) as e:
        await test_api_client.mcp.call_tool("query_completions", {"query": "SELECT * FROM whatnot"})
    assert "UNKNOWN_TABLE:" in str(e.value)
