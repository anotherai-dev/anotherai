import json
from typing import Any
from urllib.parse import quote

import pytest
from fastmcp.exceptions import ToolError
from openai import OpenAIError

from tests.components._common import IntegrationTestClient


async def _create_deployment_via_mcp(test_api_client: IntegrationTestClient, version_id: str, **kwargs: Any):
    return await test_api_client.call_tool(
        "create_or_update_deployment",
        {
            "agent_id": "test-agent",
            "version_id": version_id,
            "deployment_id": "test-agent:production#1",
            "author_name": "user",
            **kwargs,
        },
    )


async def test_create_and_use_deployment(test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call("openai", "gpt-4.1", "openai/completion.json", is_reusable=True)
    client = test_api_client.openai_client()
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ],
        temperature=0.0,
        extra_body={"agent_id": "test-agent"},
    )
    version_id = response.version_id  # pyright: ignore[reportAttributeAccessIssue]
    await test_api_client.wait_for_background()
    assert len(test_api_client.get_provider_requests("openai", "gpt-4.1")) == 1

    # Now deploy the created version via MCP
    res = await _create_deployment_via_mcp(test_api_client, version_id)
    assert res["result"]["id"] == "test-agent:production#1"
    assert res["result"]["version"]["id"] == version_id
    assert res["result"]["version"]["model"] == "gpt-4.1-latest"
    assert res["result"]["version"]["temperature"] == 0.0

    # Now we can use the deployment
    response = await client.chat.completions.create(
        model="anotherai/deployment/test-agent:production#1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, night!"},
        ],
    )
    assert response.version_id == version_id  # pyright: ignore[reportAttributeAccessIssue]

    await test_api_client.wait_for_background()

    # Check the completion
    completion = await test_api_client.get(f"/v1/completions/{response.id}")
    assert completion["agent_id"] == "test-agent"
    assert completion["version"]["id"] == version_id
    assert completion["metadata"]["anotherai/deployment_id"] == "test-agent:production#1"

    # get the last openai call, check that it contained both messages
    reqs = test_api_client.get_provider_requests("openai", "gpt-4.1")
    assert len(reqs) == 2
    req = json.loads(reqs[1].content)
    assert req["messages"] == [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, night!"},
    ]
    assert req["temperature"] == 0.0

    # Create a new completion, this time using input variables
    # Using the deployment should fail since the deployment doesn't support input variables
    with pytest.raises(OpenAIError) as e:
        await client.chat.completions.create(
            model="anotherai/deployment/test-agent:production#1",
            messages=[
                {"role": "system", "content": "You are a helpful assistant to {{name}}"},
                {"role": "user", "content": "Bye"},
            ],
            extra_body={"input": {"name": "John"}},
        )
    assert "Input variables are provided but the version does not support them" in str(e.value)
    await test_api_client.wait_for_background()

    # but using the model should succeed
    response2 = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a helpful assistant to {{name}}"},
            {"role": "user", "content": "Bye"},
        ],
        extra_body={"input": {"name": "John"}, "agent_id": "test-agent"},
    )
    await test_api_client.wait_for_background()

    completion2 = await test_api_client.get(f"/v1/completions/{response2.id}")
    assert completion2["agent_id"] == "test-agent"
    assert completion2["version"]["id"] == response2.version_id  # pyright: ignore[reportAttributeAccessIssue]
    assert completion2["input"]["variables"] == {"name": "John"}
    assert len(completion2["version"]["prompt"]) == 1

    # Trying to use the same deployment id should fail since the inputs are different
    with pytest.raises(ToolError) as e:
        await _create_deployment_via_mcp(test_api_client, completion2["version"]["id"])
    assert "The version you are trying to deploy expects input variables" in str(e.value)

    # But I can create a new deployment
    dep2 = await _create_deployment_via_mcp(test_api_client, completion2["version"]["id"], deployment_id="dep2")
    assert dep2["result"]["id"] == "dep2"
    assert dep2["result"]["version"]["id"] == completion2["version"]["id"]

    # I can use the new deployment
    response3 = await client.chat.completions.create(
        model="anotherai/deployment/dep2",
        messages=[
            # Should not have to supply the system message since it's in the deployment
            {"role": "user", "content": "Bye bye"},
        ],
        extra_body={"input": {"name": "James"}},
    )
    await test_api_client.wait_for_background()
    assert response3.version_id == dep2["result"]["version"]["id"]  # pyright: ignore[reportAttributeAccessIssue]
    reqs = test_api_client.get_provider_requests("openai", "gpt-4.1")
    assert len(reqs) == 4
    req = json.loads(reqs[-1].content)
    assert req["messages"] == [
        {"role": "system", "content": "You are a helpful assistant to James"},
        {"role": "user", "content": "Bye bye"},
    ]
    assert req["temperature"] == 1.0  # temp should be 1 here, since we did not provide it above

    # Now list the deployments
    deployments = await test_api_client.get("/v1/deployments")
    assert len(deployments["items"]) == 2
    assert deployments["items"][0]["id"] == "dep2"
    assert deployments["items"][1]["id"] == "test-agent:production#1"

    # An archive the last deployment
    await test_api_client.post(f"/v1/deployments/{quote('test-agent:production#1')}/archive")

    # It should no longer be in the list
    deployments = await test_api_client.get("/v1/deployments")
    assert len(deployments["items"]) == 1
    assert deployments["items"][0]["id"] == "dep2"

    # Finally let's update the deployment

    response4 = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            # Different prompt
            {"role": "system", "content": "You are a helpful story teller to {{name}}"},
            {"role": "user", "content": "Bye"},
        ],
        extra_body={"input": {"name": "John"}, "agent_id": "test-agent"},
    )
    await test_api_client.wait_for_background()
    # Update the deployment 2
    update_res = await _create_deployment_via_mcp(test_api_client, response4.version_id, deployment_id="dep2")  # pyright: ignore[reportAttributeAccessIssue]
    # Response is a string to redirect to the website
    assert isinstance(update_res["result"], str)
    assert "An existing deployment already exists" in update_res["result"]
    assert "deployment_id=dep2" in update_res["result"]
    assert f"completion_id={response4.id}" in update_res["result"]

    completion4 = await test_api_client.get(f"/v1/completions/{response4.id}")

    # The website will call the patch method
    updated = await test_api_client.patch(
        "/v1/deployments/dep2",
        json={
            "version": completion4["version"],
        },
    )
    assert updated["version"]["prompt"] == completion4["version"]["prompt"]
    response5 = await client.chat.completions.create(
        model="anotherai/deployment/dep2",
        messages=[
            # Should not have to supply the system message since it's in the deployment
            {"role": "user", "content": "Byeeeee"},
        ],
        extra_body={"input": {"name": "James"}},
    )
    assert response5.version_id == completion4["version"]["id"]  # pyright: ignore[reportAttributeAccessIssue]
    reqs = test_api_client.get_provider_requests("openai", "gpt-4.1")
    assert len(reqs) == 6
    req = json.loads(reqs[-1].content)
    assert req["messages"] == [
        {"role": "system", "content": "You are a helpful story teller to James"},
        {"role": "user", "content": "Byeeeee"},
    ]


async def test_deployment_archive(test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call("openai", "gpt-4.1", "openai/completion.json", is_reusable=True)
    client = test_api_client.openai_client()

    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": "Hello, world!"}],
        extra_body={"agent_id": "test-agent"},
    )
    await test_api_client.wait_for_background()
    version_id = response.version_id  # pyright: ignore[reportAttributeAccessIssue]

    # Try and deploy the version but for a different agent
    with pytest.raises(ToolError) as e:
        await _create_deployment_via_mcp(test_api_client, version_id, agent_id="test-agent-2")
    assert f"Version {version_id} not found for agent test-agent-2" in str(e.value)

    # Now deploy for real
    await _create_deployment_via_mcp(test_api_client, version_id, agent_id="test-agent")

    # Make sure we can retrieve it
    dep = await test_api_client.get(f"/v1/deployments/{quote('test-agent:production#1')}")
    assert "archived_at" not in dep

    # Now archive the deployment
    await test_api_client.post(f"/v1/deployments/{quote('test-agent:production#1')}/archive")

    # We can still retrieve it
    dep = await test_api_client.get(f"/v1/deployments/{quote('test-agent:production#1')}")
    assert "archived_at" in dep

    # And use it
    response = await client.chat.completions.create(
        model="anotherai/deployment/test-agent:production#1",
        messages=[{"role": "user", "content": "Hello, world!"}],
    )
    assert response.version_id == version_id  # pyright: ignore[reportAttributeAccessIssue]

    # But it does not show in the list
    deployments = await test_api_client.get("/v1/deployments")
    assert len(deployments["items"]) == 0

    # Now try and patch it
    response2 = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": "Hello, world!"}],
        extra_body={"agent_id": "test-agent"},
        temperature=0.5,
    )
    await test_api_client.wait_for_background()
    version_id2 = response2.version_id  # pyright: ignore[reportAttributeAccessIssue]
    assert version_id2 != version_id, "sanity check"

    dep2 = await test_api_client.patch(
        f"/v1/deployments/{quote('test-agent:production#1')}",
        json={
            # Since ID is provided it will be used to fetch an existing version
            "version": {"id": version_id2, "model": "gpt-4.1"},
        },
    )
    assert dep2["version"]["temperature"] == 0.5

    # It should no longer be archived
    deployments = await test_api_client.get("/v1/deployments")
    assert len(deployments["items"]) == 1
    dep = await test_api_client.get(f"/v1/deployments/{quote('test-agent:production#1')}")
    assert "archived_at" not in dep


async def test_deployment_from_playground(test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call("openai", "gpt-4.1", "openai/completion.json", is_reusable=True)

    # Create an experiment via the playground tool
    res = await test_api_client.call_tool(
        "playground",
        {
            "models": "gpt-4.1",
            "author_name": "user",
            "agent_id": "test-agent",
            "inputs": [
                {
                    "variables": {"name": "Toulouse"},
                },
                {
                    "variables": {"name": "Pittsburgh"},
                },
            ],
            "prompts": [
                [
                    {"role": "user", "content": "What is the capital of the country that has {{ name }}?"},
                ],
            ],
            "experiment_title": "Capital Extractor Test Experiment",
        },
    )

    completions = res["completions"]
    assert len(completions) == 2, "sanity"

    await test_api_client.wait_for_background()

    # Pull the completions to check the associated version
    completion1 = await test_api_client.get(f"/v1/completions/{completions[0]['id']}")
    completion2 = await test_api_client.get(f"/v1/completions/{completions[1]['id']}")
    assert completion1["version"]["id"] == completion2["version"]["id"], "sanity"

    # Now deploy the version
    await _create_deployment_via_mcp(test_api_client, completion1["version"]["id"], agent_id="test-agent")

    # We can use the deployment
    response = await test_api_client.openai_client().chat.completions.create(
        model="anotherai/deployment/test-agent:production#1",
        messages=[],
        extra_body={"input": {"name": "Toulouse"}},
    )
    assert response.version_id == completion1["version"]["id"]  # pyright: ignore[reportAttributeAccessIssue]
