import os

from openai import AsyncOpenAI

from core.consts import ANOTHERAI_API_URL

client = AsyncOpenAI(
    api_key=os.environ.get("ANOTHERAI_API_KEY", ""),
    base_url=f"{ANOTHERAI_API_URL}/v1/",
)
