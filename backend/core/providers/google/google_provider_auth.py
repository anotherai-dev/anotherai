import json

from cachetools import LRUCache
from google.auth.transport.requests import Request
from google.oauth2 import service_account

# Caching the last 100 tokens
# In practice, we should not have too many service accounts
_credential_cache: LRUCache[str, service_account.Credentials] = LRUCache(maxsize=100)


def _get_token_from_credentials(credentials: service_account.Credentials) -> str:
    return credentials.token  # pyright: ignore [reportUnknownVariableType, reportUnknownMemberType]


async def get_token(service_account_info: str) -> str:
    json_obj = json.loads(service_account_info)
    credentials: service_account.Credentials | None = _credential_cache.get(service_account_info)

    if credentials and credentials.valid:
        return _get_token_from_credentials(credentials)

    if not credentials:
        credentials = service_account.Credentials.from_service_account_info(  # pyright: ignore [reportUnknownMemberType]
            json_obj,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        _credential_cache[service_account_info] = credentials

    credentials.refresh(Request())  # pyright: ignore [reportUnknownMemberType]

    return _get_token_from_credentials(credentials)
