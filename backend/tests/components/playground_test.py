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
            "inputs": [{"alias": "Toulouse", "variables": {"name": "Toulouse"}}, {"variables": {"name": "Pittsburgh"}}],
        },
    )
    assert len(inserted_inputs["result"]) == 2

    # Then add 4 versions
    inserted_versions = await test_api_client.call_tool(
        "add_versions_to_experiment",
        {
            "experiment_id": experiment_id,
            "version": {
                "alias": "claude-4",
                "model": Model.CLAUDE_4_SONNET_20250514,
                "prompt": [{"role": "user", "content": "What is the capital of the country that has {{ name }}?"}],
                "temperature": 0.5,
            },
            "overrides": [
                {"alias": "claude-4-temp-1", "temperature": 1.0},
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

    assert len(res["completions"]) == 8

    # I can also fetch the experiment
    exp = await test_api_client.get(f"/v1/experiments/{res['id']}")
    assert exp["title"] == "Capital Extractor Test Experiment"
    assert len(exp["versions"]) == 4
    assert len(exp["inputs"]) == 2
    assert len(exp["completions"]) == 8

    assert sorted((i for i in exp["inputs"]), key=lambda i: i["id"]) == [
        {
            "alias": "Toulouse",
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

    assert len(res["completions"]) == 2

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
    assert len(res1["completions"]) == 4

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

    assert len(res2["completions"]) == 2  # 2 inputs * 1 model

    # Add an annotation on a run
    await test_api_client.call_tool(
        "add_annotations",
        {
            "annotations": [
                {
                    "text": "This is a test annotation",
                    "author_name": "user",
                    "target": {
                        "completion_id": res2["completions"][0]["id"],
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


async def test_image_url_as_url_object(test_api_client: IntegrationTestClient):
    res = await test_api_client.call_tool(
        "create_experiment",
        {
            "id": "test-experiment",
            "title": "Capital Extractor Test Experiment",
            "description": "This is a test experiment",
            "author_name": "user",
            "agent_id": "test-agent",
        },
    )
    experiment_id = res["id"]

    versions = await test_api_client.call_tool(
        "add_versions_to_experiment",
        {
            "experiment_id": experiment_id,
            "version": {
                "model": "gpt-5-nano-2025-08-07",
                "prompt": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "{{image_url}}",
                                },
                            },
                        ],
                    },
                ],
            },
            "overrides": [
                {"model": "gpt-4.1-nano-2025-04-14"},
            ],
        },
    )
    assert len(versions["result"]) == 2

    versions2 = await test_api_client.call_tool(
        "add_versions_to_experiment",
        {
            "experiment_id": experiment_id,
            "version": '{\n  "model": "gpt-4o-mini-latest",\n  "prompt": [\n    {\n      "role": "system",\n      "content": "You are an expert in animals. Find the animal in the image"\n    },\n    {\n      "role": "user", \n      "content": [\n        {\n          "type": "image_url",\n          "image_url": {\n            "url": "{{image_url}}"\n          }\n        }\n      ]\n    }\n  ],\n  "response_format": {\n    "json_schema": {\n      "name": "AnimalClassificationOutput",\n      "schema": {\n        "type": "object",\n        "properties": {\n          "animals": {\n            "type": "array",\n            "items": {\n              "type": "object",\n              "properties": {\n                "location": {\n                  "type": "string",\n                  "enum": ["top", "bottom", "left", "right", "center"]\n                },\n                "name": {\n                  "type": "string"\n                },\n                "subspecies": {\n                  "type": "string"\n                },\n                "latin_name": {\n                  "type": "string"\n                },\n                "endangered_level": {\n                  "type": "string",\n                  "enum": ["least concern", "near threatened", "vulnerable", "endangered", "critically endangered", "extinct in the wild", "extinct"]\n                }\n              },\n              "required": ["location", "name", "endangered_level"]\n            }\n          }\n        },\n        "required": ["animals"]\n      }\n    }\n  }\n}',
            "overrides": [
                {
                    "model": "gpt-5-nano-2025-08-07",
                },
                {
                    "model": "gemini-2.0-flash-lite-001",
                },
                {
                    "model": "gpt-4.1-nano-latest",
                },
                {
                    "model": "llama4-scout-instruct-fast",
                },
                {
                    "model": "gemini-2.5-flash-lite",
                },
            ],
        },
    )
    assert len(versions2["result"]) == 6


async def test_playground_ordering(test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        Provider.OPEN_AI,
        Model.GPT_41_MINI_2025_04_14,
        "openai/completion.json",
        is_reusable=True,
    )
    # Create an experiment
    res = await test_api_client.call_tool(
        "create_experiment",
        {
            "id": "test-experiment",
            "title": "Capital Extractor Test Experiment",
            "description": "This is a test experiment",
            "author_name": "user",
            "agent_id": "test-agent",
        },
    )
    # add 2 inputs
    await test_api_client.call_tool(
        "add_inputs_to_experiment",
        {
            "experiment_id": res["id"],
            "inputs": [
                {"alias": "input_1", "variables": {"name": "Toulouse"}},
                {"alias": "input_2", "variables": {"name": "Pittsburgh"}},
            ],
        },
    )
    # add 2 versions
    await test_api_client.call_tool(
        "add_versions_to_experiment",
        {
            "experiment_id": res["id"],
            "version": {
                "alias": "version_1",
                "model": "gpt-4.1-mini-latest",
                "prompt": [
                    {
                        "role": "user",
                        "content": "What is the capital of the country that has {{ name }}?",
                    },
                ],
            },
            "overrides": [
                {"alias": "version_2", "model": "gpt-4.1-nano-latest"},
            ],
        },
    )
    await test_api_client.wait_for_background()
    exp = await test_api_client.call_tool(
        "get_experiment",
        {
            "id": res["id"],
        },
    )
    assert "completions" in exp
    assert [(c["version"]["id"], c["input"]["id"]) for c in exp["completions"]] == [
        ("version_1", "input_1"),
        ("version_2", "input_1"),
        ("version_1", "input_2"),
        ("version_2", "input_2"),
    ]

    # Now fetch by changing the order
    exp = await test_api_client.call_tool(
        "get_experiment",
        {
            "id": res["id"],
            "version_ids": ["version_2", "version_1"],
            "input_ids": ["input_2", "input_1"],
        },
    )
    assert [(c["version"]["id"], c["input"]["id"]) for c in exp["completions"]] == [
        ("version_2", "input_2"),
        ("version_1", "input_2"),
        ("version_2", "input_1"),
        ("version_1", "input_1"),
    ]
