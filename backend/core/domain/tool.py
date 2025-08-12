from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Tool(BaseModel):
    name: str = Field(description="The name of the tool")
    description: str | None = Field(default=None, description="The description of the tool")

    input_schema: dict[str, Any] = Field(description="The input class of the tool")
    output_schema: dict[str, Any] | None = Field(description="The output class of the tool")

    strict: bool | None = Field(
        default=None,
        description="Whether to use strict mode for the tool."
        "Strict mode enforces that the input schema is a strict subset of the output schema.",
    )


class HostedTool(StrEnum):
    WEB_SEARCH_GOOGLE = "@search-google"
    WEB_SEARCH_PERPLEXITY_SONAR = "@perplexity-sonar"
    WEB_SEARCH_PERPLEXITY_SONAR_REASONING = "@perplexity-sonar-reasoning"
    WEB_SEARCH_PERPLEXITY_SONAR_PRO = "@perplexity-sonar-pro"
    WEB_BROWSER_TEXT = "@browser-text"
