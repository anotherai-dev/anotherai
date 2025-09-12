from typing import Protocol


class UserManager(Protocol):
    async def close(self):
        """Closes the user manager"""
        ...

    async def validate_oauth_token(self, token: str) -> str:
        """Validates an oauth token and returns the user id"""
        ...
