# pyright: reportPrivateUsage=false

import json
import logging
import os
import unittest
from typing import Any
from unittest.mock import Mock, patch

import httpx
import pytest
from pydantic import BaseModel, ValidationError
from pytest_httpx import HTTPXMock, IteratorStream
from structlog.testing import LogCapture

from core.domain.file import File
from core.domain.message import Message, MessageDeprecated
from core.domain.models import Model, Provider
from core.domain.models.model_data import ModelData
from core.domain.models.model_data_mapping import MODEL_DATAS
from core.domain.tool import Tool
from core.providers._base.builder_context import BuilderInterface
from core.providers._base.llm_completion import LLMCompletion
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import (
    MaxTokensExceededError,
    MissingModelError,
    ModelDoesNotSupportModeError,
    ProviderBadRequestError,
    ProviderError,
    ProviderInternalError,
    ProviderInvalidFileError,
    UnknownProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers.google.google_provider import (
    GoogleProvider,
    GoogleProviderConfig,
)
from core.providers.google.google_provider_domain import (
    Blob,
    Candidate,
    CompletionRequest,
    CompletionResponse,
    Content,
    GoogleMessage,
    GoogleSystemMessage,
    Part,
    UsageMetadata,
)
from core.providers.google.vertex_base_config import _VERTEX_API_EXCLUDED_REGIONS_METADATA_KEY
from core.runners.runner_output import RunnerOutput
from tests.fake_models import fake_llm_completion
from tests.utils import mock_aiter, request_json_body


@pytest.fixture(scope="session")
def patch_google_env_vars():
    with patch.dict(
        "os.environ",
        {
            "GOOGLE_VERTEX_AI_PROJECT_ID": "worfklowai",
            "GOOGLE_VERTEX_AI_LOCATION": "us-central1",
            "GOOGLE_VERTEX_AI_CREDENTIALS": '{"type":"service_account","project_id":"worfklowai"}',
        },
    ):
        yield


@pytest.fixture(autouse=True)
def patch_google_provider_auth():
    with patch(
        "core.providers.google.google_provider_auth.get_token",
        return_value="a_token",
        autospec=True,
    ) as mock_google_provider_auth:
        yield mock_google_provider_auth


def _output_factory(raw: str):
    return json.loads(raw)


class TestGoogleProvider(unittest.TestCase):
    def test_name(self):
        """Test the name method returns the correct Provider enum."""
        assert GoogleProvider.name() == Provider.GOOGLE

    def test_required_env_vars(self):
        """Test the required_env_vars method returOpns the correct environment variables."""
        expected_vars = ["GOOGLE_VERTEX_AI_PROJECT_ID", "GOOGLE_VERTEX_AI_LOCATION", "GOOGLE_VERTEX_AI_CREDENTIALS"]
        assert GoogleProvider.required_env_vars() == expected_vars

    def test_supports_model(self):
        """Test the supports_model method returns True for a supported model
        and False for an unsupported model"""
        provider = GoogleProvider()
        assert provider.supports_model(Model.GEMINI_1_5_PRO_001)
        assert not provider.supports_model(Model.GPT_4O_2024_05_13)

    @patch.dict(
        "os.environ",
        {
            "GOOGLE_VERTEX_AI_PROJECT_ID": "test_project_id",
            "GOOGLE_VERTEX_AI_LOCATION": "test_location",
        },
    )
    async def test_default_config(self):
        """Test the _default_config method returns the correct configuration."""
        provider = GoogleProvider()
        config = provider._default_config(0)

        assert isinstance(config, GoogleProviderConfig)
        assert config.vertex_project == "test_project_id"
        assert config.vertex_location == ["test_location"]
        assert config.default_block_threshold == "BLOCK_NONE"

    async def test_parse_old_config(self):
        old_config = {
            "vertex_credentials": "k",
            "vertex_project": "p",
            "vertex_location": "l",
        }
        config = GoogleProviderConfig.model_validate(old_config)
        assert config.vertex_credentials == "k"
        assert config.vertex_project == "p"
        assert config.vertex_location == ["l"]

    async def test_parse_region_strings(self):
        old_config = {
            "vertex_credentials": "k",
            "vertex_project": "p",
            "vertex_location": "l,m",
        }
        config = GoogleProviderConfig.model_validate(old_config)
        assert config.vertex_credentials == "k"
        assert config.vertex_project == "p"
        assert config.vertex_location == ["l", "m"]

    async def test_parse_config(self):
        old_config = {
            "vertex_credentials": "k",
            "vertex_project": "p",
            "vertex_location": ["l"],
        }
        config = GoogleProviderConfig.model_validate(old_config)
        assert config.vertex_credentials == "k"
        assert config.vertex_project == "p"
        assert config.vertex_location == ["l"]


class PerCharPricing(BaseModel):
    prompt_cost_per_token: float
    completion_cost_per_token: float
    prompt_cost_per_token_over_threshold: float | None
    completion_cost_per_token_over_threshold: float | None
    cost_per_image: float | None
    cost_per_image_over_threshold: float | None


# TODO[models]: this test relies on duplicating cost data which is not ideal
MODEL_PRICES_PER_CHAR = {
    Model.GEMINI_1_5_PRO_001: PerCharPricing(
        prompt_cost_per_token=0.000_001_25,
        completion_cost_per_token=0.000_005,
        prompt_cost_per_token_over_threshold=0.000_002_5,
        completion_cost_per_token_over_threshold=0.000_01,
        cost_per_image=0.000_328_75,
        cost_per_image_over_threshold=0.000_6575,
    ),
    Model.GEMINI_1_5_PRO_PREVIEW_0409: PerCharPricing(
        prompt_cost_per_token=0.000_001_25,
        completion_cost_per_token=0.000_005,
        prompt_cost_per_token_over_threshold=0.000_002_5,
        completion_cost_per_token_over_threshold=0.000_01,
        cost_per_image=0.000_328_75,
        cost_per_image_over_threshold=0.000_6575,
    ),
    Model.GEMINI_1_5_PRO_PREVIEW_0514: PerCharPricing(
        prompt_cost_per_token=0.000_001_25,
        completion_cost_per_token=0.000_005,
        prompt_cost_per_token_over_threshold=0.000_002_5,
        completion_cost_per_token_over_threshold=0.000_01,
        cost_per_image=0.000_328_75,
        cost_per_image_over_threshold=0.000_6575,
    ),
    Model.GEMINI_1_5_FLASH_PREVIEW_0514: PerCharPricing(
        prompt_cost_per_token=0.000_000_075,
        completion_cost_per_token=0.000_000_3,
        prompt_cost_per_token_over_threshold=0.000_000_15,
        completion_cost_per_token_over_threshold=0.000_000_6,
        cost_per_image=0.000_02,
        cost_per_image_over_threshold=0.000_04,
    ),
    Model.GEMINI_1_5_FLASH_001: PerCharPricing(
        prompt_cost_per_token=0.000_000_075,
        completion_cost_per_token=0.000_000_3,
        prompt_cost_per_token_over_threshold=0.000_000_15,
        completion_cost_per_token_over_threshold=0.000_000_6,
        cost_per_image=0.000_02,
        cost_per_image_over_threshold=0.000_04,
    ),
    Model.GEMINI_1_0_PRO_001: PerCharPricing(
        prompt_cost_per_token=0.000_000_5,
        completion_cost_per_token=0.000_0015,
        prompt_cost_per_token_over_threshold=None,
        completion_cost_per_token_over_threshold=None,
        cost_per_image=None,
        cost_per_image_over_threshold=None,
    ),
    Model.GEMINI_1_0_PRO_002: PerCharPricing(
        prompt_cost_per_token=0.000_000_5,
        completion_cost_per_token=0.000_0015,
        prompt_cost_per_token_over_threshold=None,
        completion_cost_per_token_over_threshold=None,
        cost_per_image=None,
        cost_per_image_over_threshold=None,
    ),
    Model.GEMINI_2_0_FLASH_EXP: PerCharPricing(
        prompt_cost_per_token=0.0,
        completion_cost_per_token=0.0,
        prompt_cost_per_token_over_threshold=0.0,
        completion_cost_per_token_over_threshold=0.0,
        cost_per_image=0.0,
        cost_per_image_over_threshold=0.0,
    ),
    Model.GEMINI_2_0_FLASH_THINKING_EXP_1219: PerCharPricing(
        prompt_cost_per_token=0.0,
        completion_cost_per_token=0.0,
        prompt_cost_per_token_over_threshold=0.0,
        completion_cost_per_token_over_threshold=0.0,
        cost_per_image=0.0,
        cost_per_image_over_threshold=0.0,
    ),
    Model.GEMINI_2_0_FLASH_THINKING_EXP_0121: PerCharPricing(
        prompt_cost_per_token=0.0,
        completion_cost_per_token=0.0,
        prompt_cost_per_token_over_threshold=0.0,
        completion_cost_per_token_over_threshold=0.0,
        cost_per_image=0.0,
        cost_per_image_over_threshold=0.0,
    ),
    Model.GEMINI_2_0_FLASH_LITE_PREVIEW_2502: PerCharPricing(
        prompt_cost_per_token=0,
        completion_cost_per_token=0,
        prompt_cost_per_token_over_threshold=0,
        completion_cost_per_token_over_threshold=0,
        cost_per_image=0,
        cost_per_image_over_threshold=0,
    ),
    Model.GEMINI_2_0_FLASH_LITE_001: PerCharPricing(
        prompt_cost_per_token=0.075 * 0.000_001,
        completion_cost_per_token=0.3 * 0.000_001,
        prompt_cost_per_token_over_threshold=0,
        completion_cost_per_token_over_threshold=0,
        cost_per_image=0.000_096_75,
        cost_per_image_over_threshold=0,
    ),
}
MODEL_PRICES_PER_CHAR[Model.GEMINI_1_5_PRO_002] = MODEL_PRICES_PER_CHAR[Model.GEMINI_1_5_PRO_001]
MODEL_PRICES_PER_CHAR[Model.GEMINI_1_5_FLASH_002] = MODEL_PRICES_PER_CHAR[Model.GEMINI_1_5_FLASH_001]
MODEL_PRICES_PER_CHAR[Model.GEMINI_2_0_FLASH_001] = PerCharPricing(
    prompt_cost_per_token=0.15 * 0.000_001,
    completion_cost_per_token=0.60 * 0.000_001,
    prompt_cost_per_token_over_threshold=None,
    completion_cost_per_token_over_threshold=None,
    cost_per_image=0.000_193_5,
    cost_per_image_over_threshold=None,
)


def google_vertex_ai_per_char_models():
    # Only yield Gemini 2.0 Flash
    # No point in running tests for all models
    yield Model.GEMINI_2_0_FLASH_LITE_001


def _llm_completion(messages: list[dict[str, Any]], usage: LLMUsage, response: str | None = None):
    return fake_llm_completion(usage=usage, provider=Provider.GOOGLE, model=Model.GEMINI_1_5_PRO_001)


# TODO: fix
@pytest.mark.skip(reason="TODO")
class TestGoogleProviderPerCharacterCostCalculation:
    # TODO: only use static values (instead of 'prompt_cost_per_token * 10' e.g), when the codebase will be more stable.

    @pytest.mark.parametrize("model", google_vertex_ai_per_char_models())
    async def test_basic_case(self, model: Model):
        system_message = GoogleSystemMessage(
            parts=[GoogleSystemMessage.Part(text="Hello !"), GoogleSystemMessage.Part(text="World !")],
        )

        user_messages = [
            GoogleMessage(
                role="user",
                parts=[
                    Part(text="Hello !"),
                    Part(text="World !"),
                ],
            ),
            GoogleMessage(
                role="user",
                parts=[
                    Part(text="Hello !"),
                    Part(text="World !"),
                ],
            ),
        ]

        model_per_char_pricing = MODEL_PRICES_PER_CHAR[model]

        llm_usage = await GoogleProvider().compute_llm_completion_usage(
            model=model,
            completion=_llm_completion(
                messages=[system_message.model_dump(), *[message.model_dump() for message in user_messages]],
                response="Hello you !",
                usage=LLMUsage(prompt_token_count=10, completion_token_count=20),
            ),
        )

        assert llm_usage.prompt_token_count == (
            6 * 6 / 4
        )  # (6 words * 6 tokens per word with white space removed) = 36 / 4 = 9 tokens
        assert llm_usage.prompt_cost_usd == (6 * 6 / 4) * model_per_char_pricing.prompt_cost_per_token
        assert llm_usage.completion_token_count == (9 / 4)  # 9 chars / 4 = 2.25
        assert llm_usage.completion_cost_usd == (9 / 4) * model_per_char_pricing.completion_cost_per_token

    @pytest.mark.parametrize("model", google_vertex_ai_per_char_models())
    async def test_image_case(self, model: Model):
        system_message = GoogleSystemMessage(
            parts=[
                GoogleSystemMessage.Part(text="Hello !"),
                GoogleSystemMessage.Part(text="World !"),
            ],
        )

        user_messages = [
            GoogleMessage(
                role="user",
                parts=[
                    Part(text="Hello !"),
                    Part(text="World !", inlineData=Blob(mimeType="image/png", data="data")),
                    Part(inlineData=Blob(mimeType="image/png", data="data")),
                ],
            ),
            GoogleMessage(
                role="user",
                parts=[
                    Part(text="Hello !"),
                    Part(text="World !"),
                ],
            ),
        ]

        model_per_char_pricing = MODEL_PRICES_PER_CHAR[model]
        model_data = MODEL_DATAS[model]
        assert isinstance(model_data, ModelData), f"Model {model} is not a ModelData"

        if not model_data.supports_input_image:
            pytest.skip(f"Model {model} does not support input images")

        assert model_per_char_pricing.cost_per_image is not None, (
            f"Model {model} does not have a cost per image configured in the test"
        )

        llm_usage = await GoogleProvider().compute_llm_completion_usage(
            model=model,
            completion=_llm_completion(
                messages=[system_message.model_dump(), *[message.model_dump() for message in user_messages]],
                response="Hello you !",
                usage=LLMUsage(prompt_token_count=10, completion_token_count=20),
            ),
        )

        assert llm_usage.prompt_token_count == (
            6 * 6 / 4
        )  # (6 words * 6 tokens per word with white space removed) = 36 / 4 = 9 tokens
        assert llm_usage.prompt_cost_usd == ((6 * 6 / 4) * model_per_char_pricing.prompt_cost_per_token) + (
            2 * model_per_char_pricing.cost_per_image
        )
        assert llm_usage.completion_token_count == (9 / 4)  # 9 chars / 4 = 2.25
        assert (
            llm_usage.completion_cost_usd == (9 / 4) * model_per_char_pricing.completion_cost_per_token
        )  # 9 chars / 4 = 2.25 * completion cost per char

    @pytest.mark.parametrize("model", google_vertex_ai_per_char_models())
    async def test_image_case_over_threshold(self, model: Model):
        user_messages = [
            GoogleMessage(
                role="user",
                parts=[
                    Part(text="Hello " * 130000),
                    Part(inlineData=Blob(mimeType="image/png", data="data")),
                    Part(inlineData=Blob(mimeType="image/png", data="data")),
                ],
            ),
        ]

        model_per_char_pricing = MODEL_PRICES_PER_CHAR[model]
        model_data = MODEL_DATAS[model]
        assert isinstance(model_data, ModelData), f"Model {model} is not a ModelData"

        if not model_data.supports_input_image:
            pytest.skip(f"Model {model} does not support input images")

        assert model_per_char_pricing.cost_per_image is not None, (
            f"Model {model} does not have a cost per image configure in the test"
        )

        llm_usage = await GoogleProvider().compute_llm_completion_usage(
            model=model,
            completion=_llm_completion(
                messages=[message.model_dump() for message in user_messages],
                response="Hello you !",
                usage=LLMUsage(prompt_token_count=130000, completion_token_count=20),
            ),
        )

        assert llm_usage.prompt_token_count == (130000 * 5 / 4)
        assert llm_usage.prompt_cost_usd == (
            (130000 * 5 / 4)
            * (
                model_per_char_pricing.prompt_cost_per_token_over_threshold
                or model_per_char_pricing.prompt_cost_per_token
            )
        ) + (2 * (model_per_char_pricing.cost_per_image_over_threshold or model_per_char_pricing.cost_per_image))

        assert llm_usage.completion_token_count == (9 / 4)  # 9 chars / 4 = 2.25
        assert llm_usage.completion_cost_usd == (9 / 4) * (
            model_per_char_pricing.completion_cost_per_token_over_threshold
            or model_per_char_pricing.completion_cost_per_token
        )

    @pytest.mark.parametrize("model", google_vertex_ai_per_char_models())
    async def test_raise_if_unparsable_message(self, model: Model):
        with pytest.raises(ValidationError):
            await GoogleProvider().compute_llm_completion_usage(
                model=model,
                completion=_llm_completion(
                    messages=[{"unparsable": "message"}],
                    response="Hello you !",
                    usage=LLMUsage(prompt_token_count=130000, completion_token_count=20),
                ),
            )

    async def test_with_audio(self):
        user_messages = [GoogleMessage(role="user", parts=[Part(text="Hello " * 102396)])]
        # Part(inlineData=Blob(mimeType="audio/ogg", data="data")),

        provider = GoogleProvider()
        completion = _llm_completion(
            messages=[message.model_dump() for message in user_messages],
            usage=LLMUsage(),
            response="",
        )
        model = Model.GEMINI_1_5_PRO_001
        # Without the audio part, we are just under the threshold
        llm_usage = await provider.compute_llm_completion_usage(model=model, completion=completion)
        assert llm_usage.prompt_token_count == 127995
        # 0.15999376 = 127995 * 0.0000003125 * 4
        assert pytest.approx(0.15999376, 0.00001) == llm_usage.cost_usd, "sanity"  # pyright: ignore [reportUnknownMemberType]

        # # now we add the audio
        user_messages[0].parts.append(Part(inlineData=Blob(mimeType="audio/ogg", data="data")))
        completion = _llm_completion(
            messages=[message.model_dump() for message in user_messages],
            usage=LLMUsage(),
            response="",
        )
        # Patch the duration seconds to return 10 seconds -> aka 320 token
        with patch("core.providers.google.google_provider_domain.audio_duration_seconds", return_value=10):
            llm_usage = await provider.compute_llm_completion_usage(model=model, completion=completion)
        assert llm_usage.prompt_audio_token_count == 320

        # The prompt token count remains the same
        assert llm_usage.prompt_token_count == 127995 + 320
        # Now we have audio tokens
        assert llm_usage.prompt_audio_token_count == 320
        # And the cost per token has increased
        # 0.3206125 = 127995 * 0.000000625 * 4 + 0.0000625 * 10
        assert llm_usage.prompt_cost_usd == pytest.approx(0.3206125, 0.00001)  # pyright: ignore [reportUnknownMemberType]


# TODO[models]: this test relies on duplicating data that is available in the google provider
PER_TOKEN_PRICING_IGNORE_LIST = {
    Model.GEMINI_2_0_FLASH_LITE_PREVIEW_2502,
    Model.GEMINI_1_5_PRO_001,
    Model.GEMINI_1_5_PRO_002,
    Model.GEMINI_1_5_PRO_PREVIEW_0409,
    Model.GEMINI_1_5_PRO_PREVIEW_0514,
    Model.GEMINI_1_5_FLASH_PREVIEW_0514,
    Model.GEMINI_1_5_FLASH_001,
    Model.GEMINI_1_5_FLASH_002,
    Model.GEMINI_2_0_FLASH_EXP,
    Model.GEMINI_1_0_PRO_001,
    Model.GEMINI_1_0_PRO_002,
    Model.GEMINI_2_0_FLASH_THINKING_EXP_1219,
    Model.GEMINI_2_0_FLASH_THINKING_EXP_0121,
    Model.GEMINI_2_0_FLASH_LATEST,
    Model.GEMINI_2_0_PRO_EXP,
    Model.GEMINI_2_0_FLASH_001,
    Model.GEMINI_2_0_FLASH_LITE_001,
}


class PerTokenPricing(BaseModel):
    prompt_cost_per_token: float
    completion_cost_per_token: float


MODEL_PRICE_PER_TOKEN = {
    Model.LLAMA_3_2_90B: PerTokenPricing(prompt_cost_per_token=0.000_005, completion_cost_per_token=0.000_015),
    Model.LLAMA_3_1_405B: PerTokenPricing(prompt_cost_per_token=0.000_005, completion_cost_per_token=0.000_016),
}


def google_vertex_ai_per_token_models():
    # No point in running tests for all models
    yield Model.LLAMA_3_1_405B


class TestGoogleProviderPerTokenCostCalculation:
    # TODO: only use static values (instead of 'prompt_cost_per_token * 10' e.g), when the codebase will be more stable.

    @pytest.mark.parametrize("model", google_vertex_ai_per_token_models())
    async def test_basic_case_from_initial_llm_usage(self, model: Model):
        system_message = GoogleSystemMessage(
            parts=[GoogleSystemMessage.Part(text="Hello !"), GoogleSystemMessage.Part(text="World !")],
        )

        user_messages = [
            GoogleMessage(
                role="user",
                parts=[
                    Part(text="Hello !"),
                    Part(text="World !"),
                ],
            ),
            GoogleMessage(
                role="user",
                parts=[
                    Part(text="Hello !"),
                    Part(text="World !"),
                ],
            ),
        ]

        model_per_char_pricing = MODEL_PRICE_PER_TOKEN[model]

        llm_usage = await GoogleProvider().compute_llm_completion_usage(
            model=model,
            completion=_llm_completion(
                messages=[system_message.model_dump(), *[message.model_dump() for message in user_messages]],
                response="Hello you !",
                usage=LLMUsage(prompt_token_count=14, completion_token_count=20),
            ),
        )

        assert llm_usage.prompt_token_count == 14  # From the initial LLM usage
        assert llm_usage.prompt_cost_usd == 14 * model_per_char_pricing.prompt_cost_per_token

        assert llm_usage.completion_token_count == 20
        assert llm_usage.completion_cost_usd == 20 * model_per_char_pricing.completion_cost_per_token

    # TODO: fix
    @pytest.mark.skip(reason="TODO")
    @pytest.mark.parametrize("model", google_vertex_ai_per_token_models())
    async def test_basic_case_no_initial_llm_usage(self, model: Model):
        system_message = GoogleSystemMessage(
            parts=[GoogleSystemMessage.Part(text="Hello !"), GoogleSystemMessage.Part(text="World !")],
        )

        user_messages = [
            GoogleMessage(
                role="user",
                parts=[
                    Part(text="Hello !"),
                    Part(text="World !"),
                ],
            ),
            GoogleMessage(
                role="user",
                parts=[
                    Part(text="Hello !"),
                    Part(text="World !"),
                ],
            ),
        ]

        model_per_char_pricing = MODEL_PRICE_PER_TOKEN[model]

        llm_usage = await GoogleProvider().compute_llm_completion_usage(
            model=model,
            completion=_llm_completion(
                messages=[system_message.model_dump(), *[message.model_dump() for message in user_messages]],
                response="Hello you !",
                usage=LLMUsage(),
            ),
        )

        assert llm_usage.prompt_token_count == 12
        assert llm_usage.prompt_cost_usd == 12 * model_per_char_pricing.prompt_cost_per_token

        assert llm_usage.completion_token_count == 3
        assert llm_usage.completion_cost_usd == 3 * model_per_char_pricing.completion_cost_per_token


class TestWrapSSE:
    async def test_vertex_ai(self):
        iter = mock_aiter(
            b"data: 1",
            b"2\n\ndata: 3\r\n\r\n",
        )

        wrapped = GoogleProvider().wrap_sse(iter)
        chunks = [chunk async for chunk in wrapped]
        assert chunks == [b"12", b"3"]

    async def test_multiple_events_in_single_chunk(self):
        iter = mock_aiter(
            b"data: 1\n\ndata: 2\n\ndata: 3\r\n\r\n",
        )
        chunks = [chunk async for chunk in GoogleProvider().wrap_sse(iter)]
        assert chunks == [b"1", b"2", b"3"]

    async def test_split_at_newline(self):
        # Test that we correctly handle when a split happens between the new line chars
        iter = mock_aiter(
            b"data: 1\n",
            b"\ndata: 2\r\n\r\n",
        )
        chunks = [chunk async for chunk in GoogleProvider().wrap_sse(iter)]
        assert chunks == [b"1", b"2"]


def test_compute_prompt_token_count_per_char() -> None:
    system_message = GoogleSystemMessage(
        parts=[
            GoogleSystemMessage.Part(text="Hello !"),
            GoogleSystemMessage.Part(text="World !"),
        ],
    )

    user_messages = [
        GoogleMessage(
            role="user",
            parts=[
                Part(text="Hello !"),
                Part(text="World !", inlineData=Blob(mimeType="image/png", data="data")),
                Part(inlineData=Blob(mimeType="image/png", data="data")),
            ],
        ),
        GoogleMessage(
            role="user",
            parts=[
                Part(text="Hello !"),
                Part(text="World !"),
            ],
        ),
    ]

    raw_message = [system_message.model_dump(), *[message.model_dump() for message in user_messages]]

    token_count = GoogleProvider()._compute_prompt_token_count(raw_message, Model.GEMINI_1_5_PRO_001)  # type: ignore

    assert token_count == (6 * 6 / 4)


async def test_complete_500(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://us-central1-aiplatform.googleapis.com/v1/projects/worfklowai/locations/us-central1/publishers/google/models/gemini-1.5-pro-001:generateContent",
        status_code=500,
        text="Internal Server Error",
    )

    provider = GoogleProvider(
        config=GoogleProviderConfig(
            vertex_project="worfklowai",
            vertex_credentials=os.environ["GOOGLE_VERTEX_AI_CREDENTIALS"],
            vertex_location=["us-central1"],
        ),
    )

    with pytest.raises(ProviderInternalError) as e:
        await provider.complete(
            [Message.with_text("Hello")],
            options=ProviderOptions(model=Model.GEMINI_1_5_PRO_001, max_tokens=10, temperature=0),
            output_factory=_output_factory,
        )

    details = e.value.serialized().details
    assert details
    assert details.get("provider_error") == {"raw": "Internal Server Error"}


@pytest.fixture
def mock_logger():
    return Mock(spec=logging.Logger)


@pytest.fixture
def google_provider(mock_logger: Mock):
    provider = GoogleProvider(
        config=GoogleProviderConfig(
            vertex_project="test_project",
            vertex_credentials="",
            default_block_threshold="BLOCK_NONE",
            vertex_location=["us-central1"],
        ),
        config_id=None,
    )
    provider.logger = mock_logger
    return provider


@pytest.fixture
def builder_context(google_provider: GoogleProvider):
    class Context(BaseModel):
        id: str = ""
        llm_completions: list[LLMCompletion]
        config_id: str | None
        metadata: dict[str, Any] = {}

        def add_metadata(self, key: str, value: Any) -> None:
            self.metadata[key] = value

        def get_metadata(self, key: str) -> Any | None:
            return self.metadata.get(key)

    with patch.object(google_provider, "_builder_context") as mock_builder_context:
        ctx = Context(llm_completions=[], config_id=None)
        mock_builder_context.return_value = ctx
        yield ctx


class TestExtractContentStr:
    def test_absent_json_does_not_raise(self, google_provider: GoogleProvider, log_capture: LogCapture):
        # An absent JSON is caught upstream so this function should not raise
        response = CompletionResponse(
            candidates=[Candidate(content=Content(parts=[Part(text="Hello")], role="user"))],
            usageMetadata=UsageMetadata(promptTokenCount=1, candidatesTokenCount=1),
        )

        res = google_provider._extract_content_str(response)
        assert res == "Hello"
        assert len(log_capture.entries) == 0

    def test_missing_candidates_raises(self, google_provider: GoogleProvider, mock_logger: Mock):
        # A missing candidate is caught should raise and trigger a warning
        response = CompletionResponse(
            candidates=[],
            usageMetadata=UsageMetadata(promptTokenCount=1, candidatesTokenCount=1),
        )

        with pytest.raises(UnknownProviderError):
            _ = google_provider._extract_content_str(response)

        mock_logger.warning.assert_called_once()

    def test_missing_content_does_not_raise(self, google_provider: GoogleProvider, mock_logger: Mock):
        # A missing content is caught should raise and trigger a warning
        response = CompletionResponse(
            candidates=[Candidate(content=Content(parts=[], role="user"))],
            usageMetadata=UsageMetadata(promptTokenCount=1, candidatesTokenCount=1),
        )

        # We can get a null content with a usage
        raw = google_provider._extract_content_str(response)
        assert raw == ""

        mock_logger.warning.assert_called_once()


class TestExtractStreamDelta:
    def test_extract_stream_delta_successful(self, google_provider: GoogleProvider):
        sse_event = json.dumps(
            {
                "candidates": [{"content": {"parts": [{"text": "Hello, world!"}], "role": "model"}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
            },
        ).encode()

        result = google_provider._extract_stream_delta(sse_event)

        assert result.delta == "Hello, world!"
        assert result.usage
        assert result.usage.prompt_token_count == 10
        assert result.usage.completion_token_count == 3

    def test_extract_stream_delta_recitation_error(self, google_provider: GoogleProvider):
        sse_event_recitation = json.dumps(
            {
                "candidates": [
                    {
                        "content": {"parts": [], "role": "model"},  # Add empty parts and role
                        "finishReason": "RECITATION",
                    },
                ],
            },
        ).encode()

        result = google_provider._extract_stream_delta(
            sse_event_recitation,
        )

        assert result.finish_reason == "recitation"

    def test_extract_stream_delta_max_tokens(self, google_provider: GoogleProvider):
        sse_event_max_tokens = json.dumps(
            {
                "candidates": [
                    {"content": {"parts": [{"text": "Hello, world!"}], "role": "model"}, "finishReason": "MAX_TOKENS"},
                ],
            },
        ).encode()

        result = google_provider._extract_stream_delta(
            sse_event_max_tokens,
        )

        assert result.finish_reason == "max_context"

    def test_extract_stream_delta_malformed_function_call(self, google_provider: GoogleProvider):
        sse_event_malformed_function_call = json.dumps(
            {
                "candidates": [
                    {
                        "content": {"parts": [{"text": "Hello, world!"}], "role": "model"},
                        "finishReason": "MALFORMED_FUNCTION_CALL",
                    },
                ],
            },
        ).encode()

        result = google_provider._extract_stream_delta(
            sse_event_malformed_function_call,
        )
        assert result.finish_reason == "malformed_function_call"

    def test_extract_stream_delta_empty_response(self, google_provider: GoogleProvider):
        sse_event_empty = json.dumps({"candidates": []}).encode()

        result_empty = google_provider._extract_stream_delta(
            sse_event_empty,
        )
        assert result_empty.is_empty()

    def test_no_candidates(self, google_provider: GoogleProvider):
        """Test that we currently handle the case where there are no candidates but a usage"""
        sse_event_no_candidates = json.dumps(
            {
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
            },
        ).encode()

        result_no_candidates = google_provider._extract_stream_delta(
            sse_event_no_candidates,
        )
        assert result_no_candidates.usage
        assert result_no_candidates.delta is None
        assert result_no_candidates.usage.prompt_token_count == 10
        assert result_no_candidates.usage.completion_token_count == 3


class TestComplete:
    # TODO[max-tokens]: Re-add test
    # @pytest.mark.parametrize("provider, model", list_google_provider_x_models())
    # async def test_complete_with_max_tokens_in_request(
    #     self,
    #     httpx_mock: HTTPXMock,
    #     provider: Any,
    #     model: Model,
    # ):
    #     if isinstance(provider, GoogleProvider):
    #         httpx_mock.add_response(
    #             url=f"https://us-central1-aiplatform.googleapis.com/v1/projects/worfklowai/locations/us-central1/publishers/{TEST_PUBLISHER_OVERRIDES.get(model, "google")}/models/{TEST_MODEL_STR_OVERRIDES.get(model, model.value)}:generateContent",
    #             status_code=200,
    #             json={
    #                 "candidates": [{"content": {"parts": [{"text": '{"hello": "world"}'}], "role": "model"}}],
    #                 "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
    #             },
    #         )
    #     else:
    #         httpx_mock.add_response(
    #             url=f"https://generativelanguage.googleapis.com/{TEST_PUBLISHER_OVERRIDES_GEMINI.get(model, "v1beta")}/models/{model.value}:generateContent?key=sk-proj-123",
    #             status_code=200,
    #             json={
    #                 "candidates": [{"content": {"parts": [{"text": '{"hello": "world"}'}], "role": "model"}}],
    #                 "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
    #             },
    #         )
    #     o = await provider.complete(
    #         messages=[Message(role=Message.Role.USER, content="Hello")],
    #         options=ProviderOptions(model=model, max_tokens=10, temperature=0),
    #         output_factory=_output_factory,  # pyright: ignore
    #     )
    #     assert o.output == {"hello": "world"}

    #     request = httpx_mock.get_request()
    #     assert request is not None
    #     body = request_json_body(request)
    #     assert body["generationConfig"]["maxOutputTokens"] == 10

    # @pytest.mark.parametrize("provider, model", list_google_provider_x_models())
    # async def test_complete_with_max_tokens_in_request_without_max_tokens_in_options(
    #     self,
    #     httpx_mock: HTTPXMock,
    #     provider: Any,
    #     model: Model,
    # ):
    #     if isinstance(provider, GoogleProvider):
    #         httpx_mock.add_response(
    #             url=f"https://us-central1-aiplatform.googleapis.com/v1/projects/worfklowai/locations/us-central1/publishers/{TEST_PUBLISHER_OVERRIDES.get(model, "google")}/models/{TEST_MODEL_STR_OVERRIDES.get(model, model.value)}:generateContent",
    #             status_code=200,
    #             json={
    #                 "candidates": [{"content": {"parts": [{"text": '{"hello": "world"}'}], "role": "model"}}],
    #                 "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
    #             },
    #         )
    #     else:
    #         httpx_mock.add_response(
    #             url=f"https://generativelanguage.googleapis.com/{TEST_PUBLISHER_OVERRIDES_GEMINI.get(model, "v1beta")}/models/{model.value}:generateContent?key=sk-proj-123",
    #             status_code=200,
    #             json={
    #                 "candidates": [{"content": {"parts": [{"text": '{"hello": "world"}'}], "role": "model"}}],
    #                 "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
    #             },
    #         )

    #     o = await provider.complete(
    #         messages=[Message(role=Message.Role.USER, content="Hello")],
    #         options=ProviderOptions(model=model, temperature=0),
    #         output_factory=_output_factory,  # pyright: ignore
    #     )
    #     assert o.output == {"hello": "world"}

    #     request = httpx_mock.get_request()
    #     assert request is not None
    #     body = request_json_body(request)
    #     model_data = get_model_data(model)
    #     assert body["generationConfig"]["maxOutputTokens"] is not None
    #     if model_data.max_tokens_data.max_output_tokens:
    #         assert body["generationConfig"]["maxOutputTokens"] == model_data.max_tokens_data.max_output_tokens
    #     else:
    #         assert body["generationConfig"]["maxOutputTokens"] == model_data.max_tokens_data.max_tokens

    async def test_complete_with_safety_settings(
        self,
        httpx_mock: HTTPXMock,
        google_provider: GoogleProvider,
    ):
        httpx_mock.add_response(
            url="https://us-central1-aiplatform.googleapis.com/v1/projects/test_project/locations/us-central1/publishers/google/models/gemini-1.5-pro-001:generateContent",
            status_code=200,
            json={
                "candidates": [{"content": {"parts": [{"text": '{"hello": "world"}'}], "role": "model"}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
            },
        )

        o = await google_provider.complete(
            messages=[Message.with_text("Hello")],
            options=ProviderOptions(model=Model.GEMINI_1_5_PRO_001, max_tokens=10, temperature=0),
            output_factory=_output_factory,
        )
        assert o.agent_output == {"hello": "world"}

        request = httpx_mock.get_request()
        assert request is not None
        body = request_json_body(request)
        assert body["safetySettings"] == [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        ]

    async def test_complete_with_safety_settings_no_blocks(
        self,
        httpx_mock: HTTPXMock,
        google_provider: GoogleProvider,
    ):
        google_provider._config.default_block_threshold = None

        httpx_mock.add_response(
            url="https://us-central1-aiplatform.googleapis.com/v1/projects/test_project/locations/us-central1/publishers/google/models/gemini-1.5-pro-001:generateContent",
            status_code=200,
            json={
                "candidates": [{"content": {"parts": [{"text": '{"hello": "world"}'}], "role": "model"}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
            },
        )

        o = await google_provider.complete(
            messages=[Message.with_text("Hello")],
            options=ProviderOptions(model=Model.GEMINI_1_5_PRO_001, max_tokens=10, temperature=0),
            output_factory=_output_factory,
        )
        assert o.agent_output == {"hello": "world"}

        request = httpx_mock.get_request()
        assert request is not None
        body = request_json_body(request)
        assert not body.get("safetySettings")

    async def test_retry_with_different_region(
        self,
        httpx_mock: HTTPXMock,
        google_provider: GoogleProvider,
        builder_context: BuilderInterface,
    ):
        google_provider._config.vertex_location = ["us-central1", "us-east1"]
        httpx_mock.add_response(
            url="https://us-central1-aiplatform.googleapis.com/v1/projects/test_project/locations/us-central1/publishers/google/models/gemini-1.5-pro-001:generateContent",
            status_code=429,
            text="Rate limit exceeded",
        )

        httpx_mock.add_response(
            url="https://us-east1-aiplatform.googleapis.com/v1/projects/test_project/locations/us-east1/publishers/google/models/gemini-1.5-pro-001:generateContent",
            status_code=200,
            json={
                "candidates": [{"content": {"parts": [{"text": '{"hello": "world"}'}], "role": "model"}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3},
            },
        )
        location_responses = ["us-central1", "us-east1"]
        location_iter = iter(location_responses)

        with patch(
            "core.providers.google.vertex_base_config.VertexBaseConfig._get_random_region",
            side_effect=lambda _: next(location_iter),  # pyright: ignore [reportUnknownLambdaType]
        ):
            result = await google_provider.complete(
                [Message.with_text("Hello")],
                options=ProviderOptions(model=Model.GEMINI_1_5_PRO_001, max_tokens=10, temperature=0),
                output_factory=_output_factory,
            )

        # Successful response from us-east1
        assert result == RunnerOutput(agent_output={"hello": "world"})

        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert "us-central1" in requests[0].url.path
        assert "us-east1" in requests[1].url.path
        assert builder_context.get_metadata(_VERTEX_API_EXCLUDED_REGIONS_METADATA_KEY) == "us-central1"

    async def test_retry_with_different_region_no_regions_left(
        self,
        httpx_mock: HTTPXMock,
        google_provider: GoogleProvider,
        builder_context: BuilderInterface,
    ):
        google_provider._config.vertex_location = ["us-central1", "us-east1"]
        httpx_mock.add_response(
            url="https://us-central1-aiplatform.googleapis.com/v1/projects/test_project/locations/us-central1/publishers/google/models/gemini-1.5-pro-001:generateContent",
            status_code=429,
            text="Rate limit exceeded",
        )

        httpx_mock.add_response(
            url="https://us-east1-aiplatform.googleapis.com/v1/projects/test_project/locations/us-east1/publishers/google/models/gemini-1.5-pro-001:generateContent",
            status_code=429,
            text="Rate limit exceeded",
        )
        location_responses = ["us-central1", "us-east1"]
        location_iter = iter(location_responses)

        with patch(
            "core.providers.google.vertex_base_config.VertexBaseConfig._get_random_region",
            side_effect=lambda _: next(location_iter),  # pyright: ignore [reportUnknownLambdaType]
        ):
            with pytest.raises(ProviderError, match=r"No available regions left to retry."):
                await google_provider.complete(
                    [Message.with_text("Hello")],
                    options=ProviderOptions(model=Model.GEMINI_1_5_PRO_001, max_tokens=10, temperature=0),
                    output_factory=_output_factory,
                )

            requests = httpx_mock.get_requests()
            assert len(requests) == 2
            assert "us-central1" in requests[0].url.path
            assert "us-east1" in requests[1].url.path
            excluded_regions = builder_context.get_metadata(_VERTEX_API_EXCLUDED_REGIONS_METADATA_KEY)
            assert excluded_regions is not None
            assert set(excluded_regions.split(",")) == {"us-east1", "us-central1"}


class TestRequiresDownloadingFile:
    @pytest.mark.parametrize(
        "file",
        [
            File(url="http://localhost/hello", content_type="audio/wav"),
            File(url="http://localhost/hello", content_type=None, format="audio"),
            File(url="http://localhost/hello", format="image"),  # no content type
        ],
    )
    def test_requires_downloading_file(self, file: File):
        assert GoogleProvider.requires_downloading_file(file, Model.GEMINI_1_5_PRO_001)

    def test_requires_downloading_file_experimental_models(self):
        assert GoogleProvider.requires_downloading_file(
            File(url="http://localhost/hello", content_type="image/png"),
            Model.GEMINI_2_0_FLASH_THINKING_EXP_1219,
        )
        assert GoogleProvider.requires_downloading_file(
            File(url="http://localhost/hello", content_type="image/png"),
            Model.GEMINI_2_0_FLASH_THINKING_EXP_0121,
        )

        assert GoogleProvider.requires_downloading_file(
            File(url="http://localhost/hello", content_type="image/png"),
            Model.GEMINI_2_0_FLASH_EXP,
        )

        assert GoogleProvider.requires_downloading_file(
            File(url="http://localhost/hello", content_type="image/png"),
            Model.GEMINI_EXP_1206,
        )

    @pytest.mark.parametrize(
        "file",
        [File(url="http://localhost/hello", content_type="image/png")],
    )
    def test_does_not_require_downloading_file(self, file: File):
        assert not GoogleProvider.requires_downloading_file(file, Model.GEMINI_1_5_PRO_001)


class TestVertexLocationRandomization:
    async def test_vertex_location_randomization(self, google_provider: GoogleProvider):
        google_provider._config.vertex_location = ["us-central1", "us-east1", "us-west1", "us-south1", "us-north1"]
        with patch("core.providers.google.google_provider.GoogleProvider.get_vertex_location") as mock_vertex_location:
            mock_vertex_location.side_effect = ["us-central1", "us-east1", "us-west1"]

            urls: list[str] = [str(google_provider._request_url(Model.GEMINI_1_5_PRO_001, False)) for _ in range(3)]

            assert len(set(urls)) == len(urls)

    async def test_vertex_location_randomization_with_last_used_location(self, google_provider: GoogleProvider):
        google_provider._config.vertex_location = ["us-central1", "us-east1", "us-west1", "us-south1", "us-north1"]
        with patch("core.providers.google.google_provider.GoogleProvider._get_metadata") as mock_get_metadata:

            def get_metadata_side_effect(key: str) -> str | None:
                if key == _VERTEX_API_EXCLUDED_REGIONS_METADATA_KEY:
                    return "us-central1,us-south1,us-north1,us-west1"
                return None

            mock_get_metadata.side_effect = get_metadata_side_effect

            url = str(google_provider._request_url(Model.GEMINI_1_5_PRO_001, False))
            assert "us-central1" not in url
            assert "us-east1" in url


class TestHandleStatusCode:
    def test_max_tokens_exceeded(self, google_provider: GoogleProvider):
        # Test MaxTokensExceededError
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "status": "INVALID_ARGUMENT",
                "message": "The input token count (1189051) exceeds the maximum number of tokens allowed (1000000).",
            },
        }
        with pytest.raises(MaxTokensExceededError):
            google_provider._handle_error_status_code(mock_response)

    def test_invalid_tool_call_count(self, google_provider: GoogleProvider):
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "status": "INVALID_ARGUMENT",
                "message": "Please ensure that the number of function response parts should be equal to number of function call parts of the function call turn.",
            },
        }
        with pytest.raises(ProviderBadRequestError):
            google_provider._handle_error_status_code(mock_response)

    def test_missing_model(self, google_provider: GoogleProvider):
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": {
                "code": 404,
                "message": "models/gemini-exp-1121 is not found for API version v1beta, or is not supported for generateContent. Call ListModels to see the list of available models and their supported methods.",
                "status": "NOT_FOUND",
            },
        }
        with pytest.raises(MissingModelError) as e:
            google_provider._handle_error_status_code(mock_response)
        assert e.value.capture
        assert e.value.should_try_next_provider

    def test_missing_model_custom_config(self, google_provider: GoogleProvider):
        google_provider._config_id = "test_config_id"
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": {
                "code": 404,
                "message": "models/gemini-exp-1121 is not found for API version v1beta, or is not supported for generateContent. Call ListModels to see the list of available models and their supported methods.",
                "status": "NOT_FOUND",
            },
        }
        with pytest.raises(MissingModelError) as e:
            google_provider._handle_error_status_code(mock_response)
        assert not e.value.capture
        assert e.value.should_try_next_provider

    def test_non_leading_vision(self, google_provider: GoogleProvider):
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "message": "Non-leading vision input which the model does not support.",
                "status": "INVALID_ARGUMENT",
            },
        }
        with pytest.raises(ModelDoesNotSupportModeError) as e:
            google_provider._handle_error_status_code(mock_response)
        assert e.value.capture
        assert e.value.should_try_next_provider

    def test_invalid_file(self, google_provider: GoogleProvider):
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "message": "Cannot fetch content from the provided URL. Please ensure the URL is valid and accessible by Vertex AI. Vertex AI respects robots.txt rules, so confirm the URL is allowed to be crawled. Status: URL_ERROR-ERROR_NOT_FOUND",
                "status": "INVALID_ARGUMENT",
            },
        }
        with pytest.raises(ProviderBadRequestError) as e:
            google_provider._handle_error_status_code(mock_response)
        assert not e.value.capture
        assert e.value.code == "invalid_file"
        assert e.value.store_task_run

    @pytest.mark.parametrize(
        "message",
        [
            "URL_TIMEOUT-TIMEOUT_FETCHPROXY",
            "URL_UNREACHABLE-UNREACHABLE_NO_RESPONSE",
            "URL_REJECTED-REJECTED_RPC_APP_ERROR",
            "URL_UNREACHABLE-UNREACHABLE_5xx",
        ],
    )
    def test_timeout_when_fetching_file(self, google_provider: GoogleProvider, message: str):
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "message": f"Cannot fetch content from the provided URL. Please ensure the URL is valid and accessible by Vertex AI. Vertex AI respects robots.txt rules, so confirm the URL is allowed to be crawled. Status: {message}",
                "status": "INVALID_ARGUMENT",
            },
        }
        with pytest.raises(ProviderInvalidFileError) as e:
            google_provider._handle_error_status_code(mock_response)
        assert not e.value.capture
        assert e.value.code == "invalid_file"
        assert e.value.store_task_run

    def test_file_too_large(self, google_provider: GoogleProvider):
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "message": "Request payload size exceeds the limit: 31457280 bytes.",
                "status": "INVALID_ARGUMENT",
            },
        }

        with pytest.raises(ProviderBadRequestError) as e:
            google_provider._handle_error_status_code(mock_response)
        assert not e.value.capture
        assert e.value.code == "bad_request"
        assert e.value.store_task_run

    @pytest.mark.parametrize(
        "message",
        [
            "The document has no pages.",
            "Unable to process input image. Please retry or report in https://developers.generativeai.google/guide/troubleshooting",
        ],
    )
    def test_invalid_file_no_pages(self, google_provider: GoogleProvider, message: str):
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "message": message,
                "status": "INVALID_ARGUMENT",
            },
        }
        with pytest.raises(ProviderInvalidFileError) as e:
            google_provider._handle_error_status_code(mock_response)
        assert not e.value.capture
        assert e.value.code == "invalid_file"


class TestBuildRequest:
    def test_build_request_with_max_output_tokens(self, google_provider: GoogleProvider):
        request = google_provider._build_request(
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(model=Model.GEMINI_1_5_PRO_001, max_tokens=10, temperature=0),
            stream=False,
        )
        assert isinstance(request, CompletionRequest)
        assert request.generationConfig.maxOutputTokens == 10

    def test_build_request_without_max_output_tokens(self, google_provider: GoogleProvider):
        request = google_provider._build_request(
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(model=Model.GEMINI_1_5_PRO_001, temperature=0),
            stream=False,
        )

        assert isinstance(request, CompletionRequest)
        assert request.generationConfig.maxOutputTokens is None

    def test_build_request_with_multiple_system_messages(self, google_provider: GoogleProvider):
        request = google_provider._build_request(
            messages=[
                MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="You are a helpful assistant."),
                MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello, world!"),
                MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="You are a helpful assistant too."),
            ],
            options=ProviderOptions(model=Model.GEMINI_1_5_PRO_001, temperature=0),
            stream=False,
        )

        assert isinstance(request, CompletionRequest)
        assert request.systemInstruction
        assert len(request.systemInstruction.parts) == 1
        assert request.systemInstruction.parts[0].text == "You are a helpful assistant."
        assert request.contents
        assert request.contents[0].parts[0].text == "Hello, world!"
        assert request.contents[1].parts[0].text == "You are a helpful assistant too."

    def test_build_request_no_messages(self, google_provider: GoogleProvider):
        request = google_provider._build_request(  # pyright: ignore[reportPrivateUsage]
            messages=[
                MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="You are a helpful assistant."),
            ],
            options=ProviderOptions(model=Model.GEMINI_1_5_PRO_001),
            stream=False,
        )
        assert isinstance(request, CompletionRequest)
        assert request.systemInstruction
        assert len(request.systemInstruction.parts) == 1
        assert request.systemInstruction.parts[0].text == "You are a helpful assistant."
        assert request.contents
        assert request.contents[0].parts[0].text == "-"

    def test_build_request_with_structured_generation_enabled(self, google_provider: GoogleProvider):
        """Test that structured generation is properly configured when enabled."""
        output_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name", "age"],
        }

        request = google_provider._build_request(
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(
                model=Model.GEMINI_2_5_FLASH,  # This model supports structured output
                structured_generation=True,
                output_schema=output_schema,
            ),
            stream=False,
        )

        assert isinstance(request, CompletionRequest)
        assert request.generationConfig.responseMimeType == "application/json"
        assert request.generationConfig.responseSchema is not None
        # Check that the schema was sanitized (Google uses capitalized types)
        assert request.generationConfig.responseSchema["type"] == "OBJECT"
        assert request.generationConfig.responseSchema["properties"]["name"]["type"] == "STRING"
        assert request.generationConfig.responseSchema["properties"]["age"]["type"] == "INTEGER"

    def test_build_request_with_structured_generation_disabled(self, google_provider: GoogleProvider):
        """Test that structured generation is not used when disabled."""
        output_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }

        request = google_provider._build_request(
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(
                model=Model.GEMINI_2_5_FLASH,  # Using a model that supports structured output for this test
                structured_generation=False,
                output_schema=output_schema,
            ),
            stream=False,
        )

        assert isinstance(request, CompletionRequest)
        # Even with structured_generation=False, JSON mode is still used when output_schema is provided
        assert request.generationConfig.responseMimeType == "application/json"
        # But responseSchema should be None since structured_generation=False
        assert request.generationConfig.responseSchema is None

    def test_build_request_with_structured_generation_no_schema(self, google_provider: GoogleProvider):
        """Test that structured generation is not used when no output schema is provided."""
        request = google_provider._build_request(
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(
                model=Model.GEMINI_2_5_FLASH,  # Using a model that supports structured output for this test
                structured_generation=True,
                output_schema=None,
            ),
            stream=False,
        )

        assert isinstance(request, CompletionRequest)
        assert request.generationConfig.responseMimeType == "text/plain"
        assert request.generationConfig.responseSchema is None

    def test_build_request_with_json_mode_and_schema(self, google_provider: GoogleProvider):
        """Test that JSON mode is used when output schema is provided but structured generation is not explicitly enabled."""
        output_schema = {
            "type": "object",
            "properties": {
                "result": {"type": "string"},
            },
        }

        request = google_provider._build_request(
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(
                model=Model.GEMINI_2_5_FLASH,  # Using a model that supports JSON mode
                output_schema=output_schema,
            ),
            stream=False,
        )

        assert isinstance(request, CompletionRequest)
        assert request.generationConfig.responseMimeType == "application/json"
        assert request.generationConfig.responseSchema is None

    def test_build_request_with_tools_and_output_schema(self, google_provider: GoogleProvider):
        """Test that MIME type is not set to JSON when tools are enabled, even with output schema."""

        tool = Tool(
            name="search",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
            },
            output_schema={},
        )

        request = google_provider._build_request(
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(
                model=Model.GEMINI_2_5_FLASH,  # Using a model that supports JSON mode
                output_schema=None,
                enabled_tools=[tool],
            ),
            stream=False,
        )

        assert isinstance(request, CompletionRequest)
        assert request.generationConfig.responseMimeType == "text/plain"
        assert request.generationConfig.responseSchema is None

    def test_build_request_structured_generation_schema_error_handling(
        self,
        google_provider: GoogleProvider,
        mock_logger: Mock,
    ):
        """Test that schema sanitization errors are handled gracefully."""
        # Create a schema that will cause an error during sanitization
        invalid_schema = {
            "type": "object",
            "properties": {
                "circular_ref": {"$ref": "#/definitions/circular_ref"},  # This will cause issues
            },
        }

        with patch(
            "core.providers.google.google_provider_utils.prepare_google_response_schema",
            side_effect=Exception("Schema sanitization error"),
        ):
            request = google_provider._build_request(
                messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
                options=ProviderOptions(
                    model=Model.GEMINI_2_5_FLASH,  # Using a model that supports structured output
                    structured_generation=True,
                    output_schema=invalid_schema,
                ),
                stream=False,
            )

        # Should fallback gracefully without structured generation
        assert isinstance(request, CompletionRequest)
        assert request.generationConfig.responseMimeType == "application/json"
        assert request.generationConfig.responseSchema is None

        # Verify that the error was logged
        mock_logger.error.assert_called_once()

    def test_build_request_with_complex_output_schema(self, google_provider: GoogleProvider):
        """Test structured generation with a complex nested schema."""
        complex_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                        "hobbies": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["name", "age"],
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "created_at": {"type": "string", "format": "date-time"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["user"],
        }

        request = google_provider._build_request(
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(
                model=Model.GEMINI_2_5_FLASH,  # Using a model that supports structured output
                structured_generation=True,
                output_schema=complex_schema,
            ),
            stream=False,
        )

        assert isinstance(request, CompletionRequest)
        assert request.generationConfig.responseMimeType == "application/json"
        assert request.generationConfig.responseSchema is not None
        # Verify the schema was properly sanitized
        assert request.generationConfig.responseSchema["type"] == "OBJECT"
        assert request.generationConfig.responseSchema["properties"]["user"]["type"] == "OBJECT"
        assert request.generationConfig.responseSchema["properties"]["user"]["properties"]["name"]["type"] == "STRING"
        assert request.generationConfig.responseSchema["properties"]["user"]["properties"]["age"]["type"] == "INTEGER"
        assert request.generationConfig.responseSchema["properties"]["user"]["properties"]["hobbies"]["type"] == "ARRAY"
        assert (
            request.generationConfig.responseSchema["properties"]["user"]["properties"]["hobbies"]["items"]["type"]
            == "STRING"
        )


class TestStream:
    # TODO: fix
    @pytest.mark.skip(reason="TODO")
    async def test_stream_with_no_candidates(
        self,
        google_provider: GoogleProvider,
        httpx_mock: HTTPXMock,
        builder_context: Any,
    ):
        """Check that we can handle when the last message has no candidates"""

        # Just mocking 2 chunks of data
        # 1 with candidates and the seconbd one with the usage
        httpx_mock.add_response(
            url="https://us-central1-aiplatform.googleapis.com/v1/projects/test_project/locations/us-central1/publishers/google/models/gemini-1.5-pro-001:streamGenerateContent?alt=sse",
            status_code=200,
            stream=IteratorStream(
                [
                    b"""data: {"candidates":[{"content":{"parts":[{"text":"{\\"hello\\": \\"world\\"}"}],"role":"model"}}]}\r\n\r\n""",
                    b"""data: {"usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 3}}\r\n\r\n""",
                ],
            ),
        )

        cs = [
            c
            async for c in google_provider.stream(
                messages=[Message.with_text("Hello")],
                options=ProviderOptions(
                    model=Model.GEMINI_1_5_PRO_001,
                    max_tokens=10,
                    temperature=0,
                    output_schema={},
                ),
                output_factory=_output_factory,
            )
        ]
        assert len(cs) == 2
        assert cs[-1].final_chunk
        assert cs[-1].final_chunk.agent_output == {"hello": "world"}

        # This is a bit weird here but the tokens in the usageMetadata is ignored since we need to recompute
        # a character count and divide by 4 for proper pricing
        assert builder_context.llm_completions[0].usage.prompt_token_count == 1.25
