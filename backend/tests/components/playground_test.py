import pytest
from fastmcp.exceptions import ToolError

from core.domain.models.models import Model
from core.domain.models.providers import Provider
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
            "experiment_id": "test-experiment",
            "title": "Capital Extractor Test Experiment",
            "description": "This is a test experiment",
            "agent_id": "test-agent",
            "author_name": "user",
        },
    )
    experiment_id = exp["experiment_id"]

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

    # Call the tool immediately, the call will wait for the completions to be done
    res = await test_api_client.call_tool(
        "get_experiment_outputs",
        {"experiment_id": experiment_id, "max_wait_time_seconds": 1},
    )

    completions = res["completions"]
    assert len(completions) == 8

    # I can also fetch the experiment
    exp = await test_api_client.get(f"/v1/experiments/{res['experiment_id']}")
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
    res = await test_api_client.call_tool(
        "playground",
        {
            "models": f"{Model.CLAUDE_4_SONNET_20250514},{Model.GPT_41_MINI_2025_04_14}",
            "author_name": "user",
            "agent_id": "test-agent",
            "prompts": [[{"role": "user", "content": "What is 2+2?"}]],
            "experiment_title": "Capital Extractor Test Experiment",
        },
    )
    completions = res["completions"]
    assert len(completions) == 2  # 2 models, 1 input
    await test_api_client.wait_for_background()

    # Fetch the experiment
    exp2 = await test_api_client.get(f"/v1/experiments/{res['experiment_id']}")
    # 2 versions, they both have an empty prompt
    assert len(exp2["versions"]) == 2
    assert all(not v.get("prompt") for v in exp2["versions"])
    assert len(exp2["inputs"]) == 1
    assert exp2["inputs"] == [
        {"id": "be705b1050eeba8c73c54bfd404070a4", "messages": [{"role": "user", "content": "What is 2+2?"}]},
    ]

    # Now retry with a complex prompt with a system message
    res2 = await test_api_client.call_tool(
        "playground",
        {
            "models": f"{Model.CLAUDE_4_SONNET_20250514},{Model.GPT_41_MINI_2025_04_14}",
            "author_name": "user",
            "agent_id": "test-agent",
            "prompts": [
                [{"role": "system", "content": "You are a math expert."}, {"role": "user", "content": "What is 2+2?"}],
                [{"role": "system", "content": "You are a math expert."}, {"role": "user", "content": "What is 4+4?"}],
            ],
            "experiment_title": "Capital Extractor Test Experiment 2",
        },
    )
    completions = res2["completions"]
    assert len(completions) == 4  # 2 models, 2 input
    await test_api_client.wait_for_background()
    # Fetch the experiment
    exp2 = await test_api_client.get(f"/v1/experiments/{res2['experiment_id']}")
    assert len(exp2["versions"]) == 2
    assert all(v["prompt"] == [{"role": "system", "content": "You are a math expert."}] for v in exp2["versions"])
    assert len(exp2["inputs"]) == 2
    sorted_inputs = sorted(exp2["inputs"], key=lambda i: i["id"])
    assert sorted_inputs == [
        {"id": "319848d64b435ae0adf10a5708a0ba5a", "messages": [{"role": "user", "content": "What is 4+4?"}]},
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
    res1 = await test_api_client.call_tool(
        "playground",
        {
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
            "experiment_title": "Capital Extractor Test Experiment 3",
        },
    )
    completions = res1["completions"]
    assert len(completions) == 4

    # Waiting for async storage
    await test_api_client.wait_for_background()

    # Now repeat with a query
    res1 = await test_api_client.call_tool(
        "playground",
        {
            "models": Model.GPT_41_MINI_2025_04_14,
            "author_name": "user",
            "agent_id": "test-agent",
            "completion_query": "SELECT * FROM completions",
            "prompts": [
                [
                    {"role": "user", "content": "What is the capital of {{ name }}?"},
                ],
            ],
            "experiment_title": "Capital Extractor Test Experiment 4",
        },
    )
    assert len(res1["completions"]) == 2  # 2 inputs * 1 model

    # Add an annotation on a run
    await test_api_client.call_tool(
        "add_annotations",
        {
            "annotations": [
                {
                    "text": "This is a test annotation",
                    "author_name": "user",
                    "target": {
                        "completion_id": completions[0]["id"],
                    },
                },
            ],
        },
    )
    await test_api_client.wait_for_background()

    # Try the raw query on annotations
    res3 = await test_api_client.call_tool(
        "playground",
        {
            "completion_query": "SELECT input_variables, input_messages FROM completions JOIN annotations ON completions.id = annotations.completion_id WHERE annotations.created_at >= now() - INTERVAL 1 DAY",
            "models": Model.GPT_41_MINI_2025_04_14,
            "author_name": "user",
            "agent_id": "test-agent",
            "prompts": [
                [
                    {"role": "user", "content": "What is {{ name }}?"},
                ],
            ],
            "experiment_title": "Capital Extractor Test Experiment 5",
        },
    )
    assert len(res3["completions"]) == 1


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
