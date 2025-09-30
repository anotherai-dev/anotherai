from pydantic import BaseModel

from ._client import client


class ModelSuggestionOutput(BaseModel):
    suggested_model: str


async def suggest_model(model: str, available_models: list[str]) -> str | None:
    completion = await client.beta.chat.completions.parse(
        model="suggest-model/gemini-2.5-flash",
        messages=[
            {
                "role": "system",
                "content": """
Suggest the closest supported model name for a given invalid model input.
Consider models that are similar to the invalid model if there is no obvious match.
""",
            },
            {
                "role": "user",
                "content": """
Invalid model: {{model}}

Available models: {{available_models}}
""",
            },
        ],
        response_format=ModelSuggestionOutput,
        extra_body={
            "input": {
                "model": model,
                "available_models": available_models,
            },
        },
        temperature=0.0,
    )
    if not completion.choices[0].message.parsed:
        return None
    return completion.choices[0].message.parsed.suggested_model
