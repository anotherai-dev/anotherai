from typing import Any

import pytest
from pydantic import BaseModel

from tests.components._common import IntegrationTestClient
from tests.components.run._base import OpenAITestCase, ProviderTestCase

_test_cases = [
    pytest.param(OpenAITestCase(), id="openai"),
]


@pytest.mark.parametrize("test_case", _test_cases)
async def test_string_completion(test_case: ProviderTestCase, test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        test_case.provider(),
        test_case.model(),
        f"{test_case.provider()}/completion.json",
    )

    client = test_api_client.openai_client()

    response = await client.chat.completions.create(
        model=test_case.model(),
        messages=[{"role": "user", "content": "Hello, world!"}],
    )

    assert response.choices[0].message.content == "The meaning of life is 42"
    assert response.choices[0].cost_usd > 0  # pyright: ignore [reportUnknownMemberType,reportAttributeAccessIssue]

    await test_api_client.wait_for_background()

    # Now fetching the run
    run = await test_api_client.get(f"/v1/completions/{response.id}")
    assert run["id"] == response.id
    assert run["input"] == {
        "id": "a0fb00af4f380639dfe4264ba020d50e",
        "messages": [
            {
                "content": "Hello, world!",
                "role": "user",
            },
        ],
    }
    assert run["output"] == {
        "messages": [
            {
                "content": "The meaning of life is 42",
                "role": "assistant",
            },
        ],
    }
    assert run["cost_usd"]


@pytest.mark.parametrize("test_case", _test_cases)
async def test_structured_output(test_case: ProviderTestCase, test_api_client: IntegrationTestClient):
    test_api_client.mock_provider_call(
        test_case.provider(),
        test_case.model(),
        f"{test_case.provider()}/structured_output.json",
    )

    class Output(BaseModel):
        name: str
        age: int

    client = test_api_client.openai_client()

    response = await client.beta.chat.completions.parse(
        model=test_case.model(),
        messages=[{"role": "user", "content": "Hello, world!"}],
        response_format=Output,
    )

    assert response.choices[0].message.parsed == Output(name="John Doe", age=30)
    assert response.choices[0].cost_usd > 0  # pyright: ignore [reportUnknownMemberType,reportAttributeAccessIssue]

    await test_api_client.wait_for_background()

    # Now fetching the run
    run = await test_api_client.get(f"/v1/completions/{response.id}")
    assert run["id"] == response.id
    assert run["input"] == {
        "id": "a0fb00af4f380639dfe4264ba020d50e",
        "messages": [
            {
                "content": "Hello, world!",
                "role": "user",
            },
        ],
    }
    assert run["output"] == {
        "messages": [
            {
                "content": {"name": "John Doe", "age": 30},
                "role": "assistant",
            },
        ],
    }
    assert run["cost_usd"]

    # Check that I can retrieve the run using a raw query
    query = "SELECT id FROM completions WHERE simpleJSONExtractInt(output_messages, 'age') = 30"
    query_result: list[dict[str, Any]] = await test_api_client.get(f"/v1/completions/query?query={query}")  # pyright: ignore [reportAssignmentType]
    assert len(query_result) == 1
    assert query_result[0]["id"] == response.id
