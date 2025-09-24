import asyncio
import base64
import os
from typing import Annotated, Literal

import typer
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel
from rich import print

load_dotenv(override=True)

client = AsyncOpenAI(
    api_key=os.environ.get("ANOTHERAI_API_KEY", ""),
    base_url=f"{os.environ['ANOTHERAI_API_URL']}/v1/",
)


class AnimalClassificationOutput(BaseModel):
    class Animal(BaseModel):
        location: Literal["top", "bottom", "left", "right", "center"]
        name: str
        subspecies: str | None = None
        latin_name: str | None = None
        endangered_level: Literal[
            "least concern",
            "near threatened",
            "vulnerable",
            "endangered",
            "critically endangered",
            "extinct in the wild",
            "extinct",
        ]

    animals: list[Animal]


async def classify_animal(image_url: str, model: str = "gpt-4.1-mini") -> AnimalClassificationOutput:
    response = await client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert in animals. Find the animal in the image",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                        },
                    },
                ],
            },
        ],
        extra_body={
            "agent_id": "animal-classifier",
        },
        response_format=AnimalClassificationOutput,
    )
    return response.choices[0].message.parsed or AnimalClassificationOutput(animals=[])


if __name__ == "__main__":

    def _main(
        image_url: Annotated[str | None, typer.Argument()] = None,
        file: Annotated[str | None, typer.Option()] = None,
        model: Annotated[str, typer.Option()] = "gpt-4o-mini",
        max_tokens: Annotated[int | None, typer.Option()] = None,
    ):
        if file:
            with open(file, "rb") as f:
                base64data = base64.b64encode(f.read()).decode("utf-8")
                extension = file.split(".")[-1]
                content_type = f"image/{extension}"
                image_url = f"data:{content_type};base64,{base64data}"
        if image_url is None:
            typer.echo("No image URL provided", err=True)
            raise typer.Exit(1)
        summary = asyncio.run(classify_animal(image_url, model))
        print(summary)

    typer.run(_main)
