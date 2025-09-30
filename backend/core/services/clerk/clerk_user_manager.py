import httpx

from core.domain.exceptions import InvalidTokenError
from core.services.user_manager import UserManager
from core.services.user_service import UserService


class ClerkUserManager(UserManager, UserService):
    def __init__(self, secret_key: str):
        self._client = httpx.AsyncClient(
            base_url="https://api.clerk.com/v1",
            headers={"Authorization": f"Bearer {secret_key}"},
        )

    async def close(self):
        await self._client.aclose()

    async def validate_oauth_token(self, token: str) -> str:
        response = await self._client.post("/oauth_applications/access_tokens/verify", json={"access_token": token})
        # TODO: add cache
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise InvalidTokenError("Invalid OAuth token") from e
            raise e

        return response.json()["subject"]
