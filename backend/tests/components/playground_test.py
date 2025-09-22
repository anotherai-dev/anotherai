import pytest
from fastmcp.exceptions import ToolError

from core.domain.models.models import Model
from core.domain.models.providers import Provider
from core.utils.uuid import uuid7
from tests.components._common import IntegrationTestClient


async def test_playground_tool(test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        Provider.ANTHROPIC,
        Model.CLAUDE_4_SONNET_20250514,
        "anthropic/completion.json",
        is_reusable=True,
    )
    test_api_client.mock_provider_call(
        Provider.OPEN_AI,
        Model.GPT_41_MINI_2025_04_14,
        "openai/completion.json",
        is_reusable=True,
    )

    # First create the experiment
    exp = await test_api_client.call_tool(
        "create_experiment",
        {
            "id": "test-experiment",
            "title": "Capital Extractor Test Experiment",
            "description": "This is a test experiment",
            "agent_id": "test-agent",
            "author_name": "user",
        },
    )
    experiment_id = exp["id"]

    # Then add two inputs
    inserted_inputs = await test_api_client.call_tool(
        "add_inputs_to_experiment",
        {
            "experiment_id": experiment_id,
            "inputs": [{"variables": {"name": "Toulouse"}}, {"variables": {"name": "Pittsburgh"}}],
        },
    )
    assert len(inserted_inputs["result"]) == 2

    # Then add 4 versions
    inserted_versions = await test_api_client.call_tool(
        "add_versions_to_experiment",
        {
            "experiment_id": experiment_id,
            "version": {
                "model": Model.CLAUDE_4_SONNET_20250514,
                "prompt": [{"role": "user", "content": "What is the capital of the country that has {{ name }}?"}],
                "temperature": 0.5,
            },
            "overrides": [
                {"temperature": 1.0},
                {"model": Model.GPT_41_MINI_2025_04_14},
                {"model": Model.GPT_41_MINI_2025_04_14, "temperature": 1.0},
            ],
        },
    )
    assert len(inserted_versions["result"]) == 4

    await test_api_client.wait_for_background()

    res = await test_api_client.call_tool(
        "get_experiment",
        {"id": experiment_id, "max_wait_time_seconds": 1},
    )

    # Try the completion query
    completions_query = res["completion_query"]
    completions = await test_api_client.call_tool(
        "query_completions",
        {"query": completions_query},
    )
    assert len(completions["rows"]) == 8

    # Try the version query
    version_query = res["version_query"]
    versions = await test_api_client.call_tool(
        "query_completions",
        {"query": version_query},
    )
    assert {v["version_id"] for v in versions["rows"]} == {
        v.removeprefix("anotherai/version/") for v in inserted_versions["result"]
    }

    # Try the input query
    input_query = res["input_query"]
    inputs = await test_api_client.call_tool(
        "query_completions",
        {"query": input_query},
    )
    assert {i["input_id"] for i in inputs["rows"]} == {
        i.removeprefix("anotherai/input/") for i in inserted_inputs["result"]
    }

    # I can also fetch the experiment
    exp = await test_api_client.get(f"/v1/experiments/{res['id']}")
    assert exp["title"] == "Capital Extractor Test Experiment"
    assert len(exp["versions"]) == 4
    assert len(exp["inputs"]) == 2
    assert len(exp["completions"]) == 8

    assert sorted((i for i in exp["inputs"]), key=lambda i: i["id"]) == [
        {
            "id": "901cd050e54511e4ef4065ddf3ddbdfd",
            "variables": {"name": "Toulouse"},
        },
        {
            "id": "bc4ad381493577d2d4654c590fff2765",
            "variables": {"name": "Pittsburgh"},
        },
    ]


async def test_with_no_variables(test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        Provider.ANTHROPIC,
        Model.CLAUDE_4_SONNET_20250514,
        "anthropic/completion.json",
        is_reusable=True,
    )
    test_api_client.mock_provider_call(
        Provider.OPEN_AI,
        Model.GPT_41_MINI_2025_04_14,
        "openai/completion.json",
        is_reusable=True,
    )
    experiment_id = str(uuid7())
    await test_api_client.call_tool(
        "create_experiment",
        {
            "id": experiment_id,
            "title": "Capital Extractor Test Experiment",
            "description": "This is a test experiment",
            "agent_id": "test-agent",
            "author_name": "user",
        },
    )
    # Add a single message input
    await test_api_client.call_tool(
        "add_inputs_to_experiment",
        {
            "experiment_id": experiment_id,
            "inputs": [{"messages": [{"role": "user", "content": "What is 2+2?"}]}],
        },
    )
    # Add a two models
    await test_api_client.call_tool(
        "add_versions_to_experiment",
        {
            "experiment_id": experiment_id,
            "version": {
                "model": Model.CLAUDE_4_SONNET_20250514,
                "prompt": [],
            },
            "overrides": [
                {"model": Model.GPT_41_MINI_2025_04_14},
            ],
        },
    )
    await test_api_client.wait_for_background()

    res = await test_api_client.call_tool(
        "get_experiment",
        {"id": experiment_id, "max_wait_time_seconds": 1},
    )
    completions_query = res["completion_query"]
    completions = await test_api_client.call_tool(
        "query_completions",
        {"query": completions_query},
    )

    assert len(completions["rows"]) == 2

    # Fetch the experiment
    exp2 = await test_api_client.get(f"/v1/experiments/{res['id']}")
    # 2 versions, they both have an empty prompt
    assert len(exp2["versions"]) == 2
    assert all(not v.get("prompt") for v in exp2["versions"])
    assert len(exp2["inputs"]) == 1
    assert exp2["inputs"] == [
        {"id": "be705b1050eeba8c73c54bfd404070a4", "messages": [{"role": "user", "content": "What is 2+2?"}]},
    ]


async def test_completion_query(test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        Provider.ANTHROPIC,
        Model.CLAUDE_4_SONNET_20250514,
        "anthropic/completion.json",
        is_reusable=True,
    )
    test_api_client.mock_provider_call(
        Provider.OPEN_AI,
        Model.GPT_41_MINI_2025_04_14,
        "openai/completion.json",
        is_reusable=True,
    )
    # Create 4 runs with 2 different inputs
    experiment_id = str(uuid7())
    await test_api_client.call_tool(
        "create_experiment",
        {
            "id": experiment_id,
            "title": "Capital Extractor Test Experiment",
            "description": "This is a test experiment",
            "agent_id": "test-agent",
            "author_name": "user",
        },
    )
    await test_api_client.call_tool(
        "add_inputs_to_experiment",
        {
            "experiment_id": experiment_id,
            "inputs": [{"variables": {"name": "Toulouse"}}, {"variables": {"name": "Pittsburgh"}}],
        },
    )
    version_res = await test_api_client.call_tool(
        "add_versions_to_experiment",
        {
            "experiment_id": experiment_id,
            "version": {
                "model": Model.CLAUDE_4_SONNET_20250514,
                "prompt": [
                    {"role": "user", "content": "What is the capital of the country that has {{ name }}?"},
                ],
            },
            "overrides": [
                {"model": Model.GPT_41_MINI_2025_04_14},
            ],
        },
    )
    await test_api_client.wait_for_background()
    res1 = await test_api_client.call_tool(
        "get_experiment",
        {"id": experiment_id, "max_wait_time_seconds": 1},
    )
    completions_query = res1["completion_query"]
    completions = await test_api_client.call_tool(
        "query_completions",
        {"query": completions_query},
    )
    assert len(completions["rows"]) == 4

    # Now repeat with a query
    experiment_id2 = str(uuid7())
    await test_api_client.call_tool(
        "create_experiment",
        {
            "id": experiment_id2,
            "title": "Capital Extractor Test Experiment",
            "description": "This is a test experiment",
            "agent_id": "test-agent",
            "author_name": "user",
        },
    )
    await test_api_client.call_tool(
        "add_inputs_to_experiment",
        {
            "experiment_id": experiment_id2,
            "query": "SELECT input_variables, input_messages FROM completions",
        },
    )
    await test_api_client.call_tool(
        "add_versions_to_experiment",
        {
            "experiment_id": experiment_id2,
            "version": version_res["result"][0],  # Use first version that was created
        },
    )
    await test_api_client.wait_for_background()
    res2 = await test_api_client.call_tool(
        "get_experiment",
        {"id": experiment_id2, "max_wait_time_seconds": 1},
    )
    query = res2["completion_query"]
    assert query

    completions = await test_api_client.call_tool(
        "query_completions",
        {"query": query},
    )
    assert len(completions["rows"]) == 2  # 2 inputs * 1 model

    # Add an annotation on a run
    await test_api_client.call_tool(
        "add_annotations",
        {
            "annotations": [
                {
                    "text": "This is a test annotation",
                    "author_name": "user",
                    "target": {
                        "completion_id": completions["rows"][0]["id"],
                    },
                },
            ],
        },
    )
    await test_api_client.wait_for_background()

    # TODO:
    # # Try the raw query on annotations
    # res3 = await test_api_client.call_tool(
    #     "playground",
    #     {
    #         "completion_query": "SELECT input_variables, input_messages FROM completions JOIN annotations ON completions.id = annotations.completion_id WHERE annotations.created_at >= now() - INTERVAL 1 DAY",
    #         "models": Model.GPT_41_MINI_2025_04_14,
    #         "author_name": "user",
    #         "agent_id": "test-agent",
    #         "prompts": [
    #             [
    #                 {"role": "user", "content": "What is {{ name }}?"},
    #             ],
    #         ],
    #         "experiment_title": "Capital Extractor Test Experiment 5",
    #     },
    # )
    # assert len(res3["completions"]) == 1


# TODO:
@pytest.mark.skip(reason="Not implemented")
async def test_use_cache(test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        Provider.ANTHROPIC,
        Model.CLAUDE_4_SONNET_20250514,
        "anthropic/completion.json",
        is_reusable=True,
    )
    test_api_client.mock_provider_call(
        Provider.OPEN_AI,
        Model.GPT_41_MINI_2025_04_14,
        "openai/completion.json",
        is_reusable=True,
    )
    playground_payload = {
        "models": f"{Model.CLAUDE_4_SONNET_20250514},{Model.GPT_41_MINI_2025_04_14}",
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
        "temperatures": "0,1.0",  # default cache setting is always
        "experiment_title": "Capital Extractor Test Experiment",
    }
    res = await test_api_client.call_tool("playground", playground_payload)
    assert len(res["completions"]) == 8
    assert len(test_api_client.get_provider_requests(Provider.ANTHROPIC, Model.CLAUDE_4_SONNET_20250514)) == 4
    assert len(test_api_client.get_provider_requests(Provider.OPEN_AI, Model.GPT_41_MINI_2025_04_14)) == 4

    # Reset the mocks
    assert len(test_api_client.httpx_mock.get_requests()) == 8

    await test_api_client.wait_for_background()
    # Try it again, the cache should be used and  no run should go through
    res = await test_api_client.call_tool("playground", playground_payload)
    assert len(res["completions"]) == 8
    assert len(test_api_client.httpx_mock.get_requests()) == 8

    # If I do the same but switch to auto, the cache is used for 4 out of 8 calls
    res = await test_api_client.call_tool("playground", {**playground_payload, "use_cache": "auto"})
    assert len(res["completions"]) == 8
    assert len(test_api_client.httpx_mock.get_requests()) == 12  # 8 + 4

    # If I do the same but switch to never, the cache is not used and 8 runs go through
    res = await test_api_client.call_tool("playground", {**playground_payload, "use_cache": "never"})
    assert len(res["completions"]) == 8
    assert len(test_api_client.httpx_mock.get_requests()) == 20  # 8 + 8


# TODO:
@pytest.mark.skip(reason="Not implemented")
async def test_with_variables(test_api_client: IntegrationTestClient):
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
    await test_api_client.wait_for_background()

    completions = res["completions"]
    assert len(completions) == 2, "sanity"

    # Pull the completions to check the associated version
    completion1 = await test_api_client.get(f"/v1/completions/{completions[0]['id']}")
    completion2 = await test_api_client.get(f"/v1/completions/{completions[1]['id']}")

    # The versions should be the same
    assert completion1["version"] == completion2["version"]
    version = completion1["version"]
    assert version["model"] == "gpt-4.1-latest"
    assert version["temperature"] == 1.0

    assert version["input_variables_schema"] == {
        "type": "object",
        "properties": {"name": {"type": "string"}},
    }


# TODO:
@pytest.mark.skip(reason="Not implemented")
async def test_playground_empty_messages(test_api_client: IntegrationTestClient):
    with pytest.raises(ToolError):
        await test_api_client.call_tool(
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
                "experiment_title": "Capital Extractor Test Experiment",
            },
        )

    assert not test_api_client.httpx_mock.get_requests()
