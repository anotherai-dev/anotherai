from typing import Any

import pytest
from httpx import HTTPStatusError

from tests.components._common import IntegrationTestClient


# TODO:
@pytest.mark.skip("Skipping for now")
async def test_create_and_annotate_experiment(test_api_client: IntegrationTestClient):
    # Create an experiment manually
    exp = await test_api_client.post(
        "/v1/experiments",
        {
            "title": "Test Experiment",
            "description": "This is a test experiment",
            "agent_id": "test-agent",
            "author_name": "Test Author",
        },
    )
    assert "id" in exp
    assert not exp.get("completions")

    # Now run a completion
    test_api_client.mock_provider_call("openai", "gpt-4.1", "openai/completion.json")
    client = test_api_client.openai_client()
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": "Hello, world!"}],
    )
    completion_id = response.id
    await test_api_client.wait_for_background()

    exp = await test_api_client.get(f"/v1/experiments/{exp['id']}")
    assert not exp.get("completions"), "sanity"

    # If I add an annotation to the completion, but not the experiment, the 2 are not linked
    _ = await test_api_client.post(
        "/v1/annotations",
        [
            {
                "target": {
                    "completion_id": completion_id,
                },
                "text": "This is a test annotation for the completion",
                "author_name": "Test Author",
            },
        ],
    )
    exp = await test_api_client.get(f"/v1/experiments/{exp['id']}")
    assert not exp.get("completions"), "completion should not be linked to the experiment"

    # Now try to add an annotation to the experiment
    _ = await test_api_client.post(
        "/v1/annotations",
        [
            {
                "target": {
                    "completion_id": completion_id,
                },
                "context": {
                    "experiment_id": exp["id"],
                },
                "text": "This is a test annotation",
                "author_name": "Test Author",
            },
        ],
    )

    # Now try to retrieve the experiment
    exp = await test_api_client.get(f"/v1/experiments/{exp['id']}")
    assert len(exp["completions"]) == 1
    assert exp["completions"][0]["id"] == completion_id
    assert len(exp["annotations"]) == 2  # 2 annotations total

    await test_api_client.wait_for_background()

    # Now let's try and query the completions
    query_for_annotations = """SELECT id FROM completions JOIN annotations ON completions.id = annotations.completion_id WHERE annotations.author_name = 'Test Author'"""
    result: list[dict[str, Any]] = await test_api_client.get(f"/v1/completions/query?query={query_for_annotations}")  # pyright: ignore [reportAssignmentType]
    assert len(result) == 2

    # Now let's try and query the experiments
    query_for_experiments = f"""SELECT version_id FROM completions WHERE id IN (SELECT arrayJoin(completion_ids) FROM experiments WHERE id = '{exp["id"]}')"""  # noqa: S608
    result = await test_api_client.get(f"/v1/completions/query?query={query_for_experiments}")  # pyright: ignore [reportAssignmentType]
    assert len(result) == 1

    # If I list all annotations for the experiment, I should get all the annotations
    annotations = await test_api_client.get(f"/v1/annotations?experiment_id={exp['id']}")
    assert len(annotations["items"]) == 2


async def test_create_experiment_user_defined_id(test_api_client: IntegrationTestClient):
    # Create an experiment manually
    exp = await test_api_client.post(
        "/v1/experiments",
        {
            "title": "Test Experiment",
            "description": "This is a test experiment",
            "agent_id": "test-agent",
            "author_name": "Test Author",
            "id": "my-experiment-id",
        },
    )
    assert "id" in exp
    assert exp["id"] == "my-experiment-id"

    # I can retrieve it
    retrieved = await test_api_client.get(
        "/v1/experiments/my-experiment-id",
    )
    assert retrieved["id"] == "my-experiment-id"

    # And if I try to create it again, it fails
    with pytest.raises(HTTPStatusError) as e:
        _ = await test_api_client.post(
            "/v1/experiments",
            {
                "title": "Test Experiment",
                "description": "This is a test experiment",
                "agent_id": "test-agent",
                "author_name": "Test Author",
                "id": "my-experiment-id",
            },
        )
    assert e.value.response.status_code == 400
