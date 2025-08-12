from pydantic import BaseModel


class Usage(BaseModel):
    text_token_count: float | None = None
    audio_token_count: float | None = None
    audio_count: int | None = None
    image_token_count: float | None = None
    image_count: int | None = None
    cost_usd: float


class PromptUsage(Usage):
    cached_token_count: float | None = None
    reasoning_token_count: float | None = None


class InferenceUsage(BaseModel):
    prompt: PromptUsage
    completion: Usage
