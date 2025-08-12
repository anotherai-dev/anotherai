import os

from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ.get("ANOTHERAI_API_KEY", ""),
    base_url=os.environ.get("ANOTHERAI_API_URL", "http://localhost:8000/v1"),
)
