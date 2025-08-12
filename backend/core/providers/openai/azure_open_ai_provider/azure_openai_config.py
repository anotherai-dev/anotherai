from typing import Literal

from pydantic import BaseModel

from core.domain.models.providers import Provider


class AzureRegionConfig(BaseModel):
    api_key: str
    url: str
    models: set[str]


class AzureOpenAIConfig(BaseModel):
    provider: Literal[Provider.AZURE_OPEN_AI] = Provider.AZURE_OPEN_AI
    deployments: dict[str, AzureRegionConfig]
    api_version: str = "2024-12-01-preview"

    def __str__(self) -> str:
        return f"AzureOpenAIConfig(deployments={list(self.deployments.keys())}, api_version={self.api_version})"
