import asyncio
import os
import sys
from typing import Annotated

import typer
from dotenv import load_dotenv
from openai import AsyncOpenAI
from rich import print

load_dotenv(override=True)

client = AsyncOpenAI(
    api_key=os.environ.get("ANOTHERAI_API_KEY", ""),
    base_url=f"{os.environ['ANOTHERAI_API_URL']}/v1/",
)


async def summarize_text(text: str, model: str = "gpt-4.1-nano", max_tokens: int | None = None) -> str:
    response = await client.chat.completions.create(
        model=model,
        max_completion_tokens=max_tokens,
        messages=[
            {
                "role": "system",
                "content": "You are an expert text summarizer. Provide a clear, concise summary of the text below, capturing the main points and key details in 2-3 sentences.",
            },
            {
                "role": "user",
                "content": "{{text}}",
            },
        ],
        extra_body={
            "agent_id": "text-summarizer",
            "input": {
                "text": text,
            },
        },
    )
    return response.choices[0].message.content or ""


if __name__ == "__main__":

    def _main(
        text: Annotated[str | None, typer.Argument()] = None,
        model: Annotated[str, typer.Option()] = "gpt-4o-mini",
        max_tokens: Annotated[int | None, typer.Option()] = None,
    ):
        if text is None and not sys.stdin.isatty():
            text = sys.stdin.read()
        if text is None:
            typer.echo("No text provided", err=True)
            raise typer.Exit(1)
        summary = asyncio.run(summarize_text(text, model, max_tokens))
        print(summary)

    typer.run(_main)
