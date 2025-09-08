from pydantic import BaseModel


class TokenUsage(BaseModel):
    text_token_count: float | None = None
    audio_token_count: float | None = None
    audio_count: int | None = None
    image_token_count: float | None = None
    image_count: int | None = None
    cost_usd: float


class CompletionUsage(TokenUsage):
    cached_token_count: float | None = None
    reasoning_token_count: float | None = None


class InferenceUsage(BaseModel):
    prompt: TokenUsage
    completion: CompletionUsage
