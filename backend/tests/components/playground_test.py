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

    res = await test_api_client.call_tool(
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
            "temperatures": "0.5,1.0",
            "experiment_title": "Capital Extractor Test Experiment",
        },
    )
    completions = res["completions"]
    assert len(completions) == 8
    await test_api_client.wait_for_background()

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
