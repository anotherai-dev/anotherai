import asyncio
import os
from datetime import UTC, datetime
from typing import TypedDict

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core.domain.models.model_data import ModelData
from core.domain.models.model_data_mapping import MODEL_DATAS, get_model_id
from core.domain.models.model_provider_data_mapping import MISTRAL_PROVIDER_DATA


class ModelCapabilities(TypedDict):
    completion_chat: bool
    completion_fim: bool
    function_calling: bool
    fine_tuning: bool
    vision: bool
    classification: bool


class MistralModel(TypedDict):
    id: str
    object: str
    created: int
    owned_by: str
    capabilities: ModelCapabilities
    name: str
    description: str
    max_context_length: int
    aliases: list[str]
    deprecation: str | None
    default_model_temperature: float
    type: str


async def _list_models() -> list[MistralModel]:
    async with httpx.AsyncClient() as client:
        url = "https://api.mistral.ai/v1/models?limit=100"
        response = await client.get(url, headers={"Authorization": f"Bearer {os.getenv('MISTRAL_API_KEY')}"})
        response.raise_for_status()
        return response.json()["data"]


_EXCLUDED_MODELS = {
    "codestral-embed",
    "codestral-embed-2505",
    "devstral-medium-2507",
    "devstral-medium-latest",
    "devstral-small-2505",
    "devstral-small-2507",
    "devstral-small-latest",
    "mistral-embed",
    "mistral-embed-2312",
    "mistral-moderation-2411",
    "mistral-moderation-latest",
    "mistral-ocr-2503",
    "mistral-ocr-2505",
    "mistral-ocr-latest",
    "mistral-tiny",
    "mistral-tiny-2312",
    "mistral-tiny-2407",
    "mistral-tiny-latest",
    "voxtral-mini-2507",
    "voxtral-mini-latest",
    "voxtral-mini-transcribe-2507",
    "voxtral-small-2507",
    "voxtral-small-latest",
    "open-mistral-nemo",
    "open-mistral-nemo-2407",
    "open-mixtral-8x22b",
    "open-mixtral-8x22b-2404",
    "open-mixtral-8x7b",
    "mistral-small-2312",
}


async def _main():  # noqa: C901
    mistral_values = await _list_models()

    errors: list[str] = []

    remaining_models = set(MISTRAL_PROVIDER_DATA.keys())
    print("found ", len(mistral_values), " models")

    for mistra_data in mistral_values:
        mistral_id = mistra_data["id"]
        if mistral_id in _EXCLUDED_MODELS:
            continue

        deprecation = datetime.fromisoformat(mistra_data["deprecation"]) if mistra_data["deprecation"] else None
        if deprecation and deprecation.date() <= datetime.now(UTC).date():
            continue

        try:
            model_id = get_model_id(mistral_id)
        except ValueError:
            errors.append(f"Model {mistral_id} is not a valid model")
            continue

        data = MODEL_DATAS[model_id]
        if not isinstance(data, ModelData):
            continue

        if aliases := mistra_data.get("aliases"):
            for alias in aliases:
                if alias in _EXCLUDED_MODELS:
                    continue
                try:
                    value = get_model_id(alias)

                    if value != model_id and value != alias:
                        errors.append(f"Alias {alias} should point to {model_id} not {value}")
                except ValueError:
                    errors.append(f"Alias {alias} is a missing alias for {mistral_id}")

        try:
            remaining_models.remove(model_id)
        except KeyError:
            continue

        if model_id not in MISTRAL_PROVIDER_DATA:
            # Model is not supported by Mistral
            errors.append(f"Model {model_id} is supported by Mistral but we don't have data for it")

        if mistra_data["capabilities"]["function_calling"] != data.supports_tool_calling:
            errors.append(
                f"Model {model_id} has a different function calling support {mistra_data['capabilities']['function_calling']} != {data.supports_tool_calling}",
            )

        if mistra_data["capabilities"]["vision"] != data.supports_input_image:
            errors.append(f"Model {model_id} has a different vision support")

        if mistra_data["max_context_length"] != data.max_tokens_data.max_tokens:
            errors.append(
                f"Model {model_id} has a different max context length: {mistra_data['max_context_length']} != {data.max_tokens_data.max_tokens}",
            )

    if remaining_models:
        errors.append(f"Models {remaining_models} seems to be missing from Mistral")

    if errors:
        console = Console()

        # Create a panel with all errors
        error_text = Text()
        for i, error in enumerate(errors, 1):
            error_text.append(f"{i:2d}. ", style="dim")
            error_text.append(error, style="red")
            if i < len(errors):
                error_text.append("\n")

        panel = Panel(
            error_text,
            title=f"[bold red]Found {len(errors)} Error{'s' if len(errors) > 1 else ''}[/bold red]",
            border_style="red",
            padding=(1, 2),
        )

        console.print(panel)
    else:
        console = Console()
        console.print("[bold green]✓ No errors found![/bold green]")


if __name__ == "__main__":
    load_dotenv(override=True)
    asyncio.run(_main())
