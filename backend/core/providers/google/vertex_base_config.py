import base64
import json
import random
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from core.providers._base.provider_error import InvalidProviderConfigError, UnknownProviderError
from core.providers._base.utils import get_provider_config_env
from core.providers.google import google_provider_auth

BLOCK_THRESHOLD = Literal["BLOCK_LOW_AND_ABOVE", "BLOCK_MEDIUM_AND_ABOVE", "BLOCK_ONLY_HIGH", "BLOCK_NONE"]


_VERTEX_API_REGION_METADATA_KEY = "workflowai.vertex_api_region"
_VERTEX_API_EXCLUDED_REGIONS_METADATA_KEY = "workflowai.vertex_api_excluded_regions"


class VertexBaseConfig(BaseModel):
    vertex_project: str
    vertex_credentials: str
    vertex_location: list[str]

    default_block_threshold: BLOCK_THRESHOLD | None = None

    def __str__(self):
        return f"{self.__class__.__name__}(project={self.vertex_project}, location={self.vertex_location[0]}, credentials=****)"

    @field_validator("vertex_location", mode="before")
    @classmethod
    def sanitize_vertex_location(cls, data: Any) -> Any:
        if isinstance(data, str):
            return data.split(",")
        return data

    def all_available_regions(self):
        return set(self.vertex_location)

    @classmethod
    def _get_random_region(cls, choices: list[str]) -> str:
        return random.choice(choices)  # noqa: S311

    def get_random_location(self, get_metadata: Callable[[str], Any | None], add_metadata: Callable[[str, Any], None]):
        used_regions = get_metadata(_VERTEX_API_EXCLUDED_REGIONS_METADATA_KEY)
        excluded_regions: set[str] = set(used_regions.split(",")) if used_regions else set()
        region = get_metadata(_VERTEX_API_REGION_METADATA_KEY)
        if region and region not in excluded_regions:
            excluded_regions.add(region)
            add_metadata(_VERTEX_API_EXCLUDED_REGIONS_METADATA_KEY, ",".join(excluded_regions))
        choices = list(self.all_available_regions() - set(excluded_regions))

        if len(choices) == 0:
            raise UnknownProviderError("No available regions left to retry.", extra={"choices": choices})
        region = self._get_random_region(choices)
        add_metadata(_VERTEX_API_REGION_METADATA_KEY, region)
        return region

    async def get_request_headers(self) -> dict[str, str]:
        token = await google_provider_auth.get_token(self.vertex_credentials)
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    @classmethod
    def required_env_vars(cls) -> list[str]:
        return ["GOOGLE_VERTEX_AI_PROJECT_ID", "GOOGLE_VERTEX_AI_LOCATION", "GOOGLE_VERTEX_AI_CREDENTIALS"]

    @classmethod
    def default(cls, index: int):
        return cls(
            vertex_project=get_provider_config_env("GOOGLE_VERTEX_AI_PROJECT_ID", index),
            vertex_credentials=get_provider_config_env("GOOGLE_VERTEX_AI_CREDENTIALS", index),
            vertex_location=get_provider_config_env("GOOGLE_VERTEX_AI_LOCATION", index).split(","),
            default_block_threshold="BLOCK_NONE",
        )

    def sanitize(self):
        credentials = self.vertex_credentials
        if not credentials.startswith("{"):
            # Credentials are not a JSON string. We assume they are base64 encoded
            # the frontend sends b64 encoded credentials
            credentials = credentials.removeprefix("data:application/json;base64,")
            try:
                credentials = base64.b64decode(credentials).decode("utf-8")
            except ValueError as e:
                raise InvalidProviderConfigError("Invalid base64 encoded credentials") from e

        try:
            raw_json = json.loads(credentials)
        except json.JSONDecodeError as e:
            raise InvalidProviderConfigError("Vertex credentials are not a json payload") from e

        if not isinstance(raw_json, dict):
            raise InvalidProviderConfigError("Vertex credentials are not a json object")

        # Check if the project matches the project in the config
        if raw_json.get("project_id") != self.vertex_project:
            raise InvalidProviderConfigError("Vertex credentials project_id does not match the project in the config")

        if "private_key" not in raw_json:
            raise InvalidProviderConfigError("Vertex credentials are missing a private_key")

        return self.__class__(
            vertex_project=self.vertex_project,
            vertex_credentials=credentials,
            vertex_location=self.vertex_location,
        )
