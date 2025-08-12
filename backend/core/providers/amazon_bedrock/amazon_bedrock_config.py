import json
from typing import Literal, cast, override

from pydantic import BaseModel, Field
from structlog import get_logger

from core.domain.exceptions import (
    MissingEnvVariablesError,
)
from core.domain.models import Model, Provider
from core.providers._base.provider_error import MissingModelError
from core.providers._base.utils import get_provider_config_env

_log = get_logger(__name__)


# A map Model -> bedrock resource id
# By default we use the cross inference resources
def _default_resource_ids():
    return {
        Model.CLAUDE_3_7_SONNET_20250219: "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        Model.CLAUDE_3_5_SONNET_20241022: "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        Model.CLAUDE_3_5_SONNET_20240620: "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
        Model.CLAUDE_3_OPUS_20240229: "us.anthropic.claude-3-opus-20240229-v1:0",
        Model.CLAUDE_3_5_HAIKU_20241022: "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        Model.CLAUDE_3_HAIKU_20240307: "us.anthropic.claude-3-haiku-20240307-v1:0",
        Model.LLAMA_3_3_70B: "us.meta.llama3-3-70b-instruct-v1:0",
        Model.LLAMA_3_1_405B: "meta.llama3-1-405b-instruct-v1:0",
        Model.LLAMA_3_1_70B: "us.meta.llama3-1-70b-instruct-v1:0",
        Model.LLAMA_3_1_8B: "us.meta.llama3-1-8b-instruct-v1:0",
        Model.MISTRAL_LARGE_2_2407: "mistral.mistral-large-2407-v1:0",
        Model.CLAUDE_4_OPUS_20250514: "us.anthropic.claude-opus-4-20250514-v1:0",
        Model.CLAUDE_4_SONNET_20250514: "us.anthropic.claude-sonnet-4-20250514-v1:0",
    }


class AmazonBedrockConfig(BaseModel):
    provider: Literal[Provider.AMAZON_BEDROCK] = Provider.AMAZON_BEDROCK

    api_key: str
    resource_id_x_model_map: dict[Model, str] = Field(default_factory=_default_resource_ids)
    available_model_x_region_map: dict[Model, str] = Field(default_factory=dict)
    default_region: str = "us-west-2"

    @override
    def __str__(self):
        models = [model.value for model in self.available_model_x_region_map]
        regions = set(self.available_model_x_region_map.values())
        return (
            f"AmazonBedrockConfig(api_key={self.api_key[:4]}****, "
            f"available_models={models}, available_regions={regions})"
        )

    @classmethod
    def from_env(cls, index: int):
        def _map_model_map(key: str, default: dict[Model, str]) -> dict[Model, str]:
            try:
                value = get_provider_config_env(key, index)
            except MissingEnvVariablesError:
                return default
            try:
                d = json.loads(value)
            except json.JSONDecodeError:
                _log.exception("Invalid model mapping. Must be a json object of model names to deployment names")
                return default
            if not isinstance(d, dict):
                _log.error(
                    "Invalid model mapping. Must be a json object of model names to deployment names",
                    raw_models=value,
                )
                return default
            out: dict[Model, str] = {}
            for k, v in cast(dict[str, str], d).items():
                try:
                    out[Model(k)] = v
                except ValueError:
                    _log.warning(
                        "Invalid model name in model mapping, Skipping",
                        model=k,
                    )
            return out

        return cls(
            api_key=get_provider_config_env("AWS_BEDROCK_API_KEY", index),
            available_model_x_region_map=_map_model_map("AWS_BEDROCK_MODEL_REGION_MAP", {}),
            resource_id_x_model_map=_map_model_map("AWS_BEDROCK_RESOURCE_ID_MODEL_MAP", _default_resource_ids()),
            default_region=get_provider_config_env("AWS_BEDROCK_DEFAULT_REGION", index, "us-west-2"),
        )

    def region_for_model(self, model: Model):
        return self.available_model_x_region_map.get(model, self.default_region)

    def id_for_model(self, model: Model):
        try:
            return self.resource_id_x_model_map[model]
        except KeyError:
            raise MissingModelError(
                f"Model {model} is not supported by Amazon Bedrock",
                extras={"model": model},
            ) from None
