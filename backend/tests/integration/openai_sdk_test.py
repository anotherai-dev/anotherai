import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel

from core.domain.models.models import Model
from core.domain.models.providers import Provider
from tests.integration.conftest import MODEL_PROVIDERS


@pytest.mark.parametrize(("provider", "model"), MODEL_PROVIDERS)
async def test_raw_string_completion(provider: Provider, model: Model, openai_client: AsyncOpenAI):
    res = await openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "What is the meaning of life?"}],
        extra_body={
            "provider": provider,
            "use_fallback": "never",
            "use_cache": "never",
            "agent_id": "test_raw_string_completion",
        },
        metadata={"provider": provider},
    )
    assert res.choices[0].message.content
    assert res.choices[0].cost_usd > 0  # pyright: ignore [reportAttributeAccessIssue]


@pytest.mark.parametrize(("provider", "model"), MODEL_PROVIDERS)
async def test_structured_output(provider: Provider, model: Model, openai_client: AsyncOpenAI):
    class Output(BaseModel):
        capital: str
        country: str

    res = await openai_client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": "Given a city, give the country it belongs to and its capital."},
            {"role": "user", "content": "Toulouse"},
        ],
        extra_body={
            "provider": provider,
            "use_fallback": "never",
            "use_cache": "never",
            "agent_id": "test_structured_output",
        },
        metadata={"provider": provider},
        response_format=Output,
    )
    assert res.choices[0].message.parsed
    assert res.choices[0].message.parsed.capital == "Paris"
    assert res.choices[0].message.parsed.country == "France"
