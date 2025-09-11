import binascii
import json
from typing import Any, NotRequired, Protocol, TypedDict, override

from jwt import InvalidTokenError as JWTInvalidTokenError
from jwt import PyJWK, PyJWKClient, decode

from core.domain.exceptions import InvalidTokenError
from core.utils.strings import b64_urldecode


class SignatureVerifier(Protocol):
    async def verify(self, token: str) -> dict[str, Any]: ...


class _Header(TypedDict):
    kid: NotRequired[str]
    alg: NotRequired[str]


def headers(token: str) -> _Header:
    splits = token.split(".")
    if len(splits) != 3:
        raise InvalidTokenError("Invalid bearer token. Provide either an API key (aai-***) or a JWT", capture=True)
    try:
        return json.loads(b64_urldecode(splits[0]))
    except (IndexError, ValueError, binascii.Error, json.JSONDecodeError) as e:
        raise InvalidTokenError("Token does not have a valid header") from e


class JWKSetSignatureVerifier(SignatureVerifier):
    def __init__(self, url: str):
        self._jwk_client: PyJWKClient = PyJWKClient(uri=url, cache_keys=True, cache_jwk_set=True, max_cached_keys=16)

    @override
    async def verify(self, token: str) -> dict[str, Any]:
        # TODO: not super optimal here, the http call is done synchronously
        # Should be ok since we're using a cache
        header = headers(token)
        kid = header.get("kid")
        alg = header.get("alg")
        if not kid:
            raise InvalidTokenError("Token does not have a valid kid", capture=True)
        signing_key = self._jwk_client.get_signing_key(kid)
        return _decode(token, signing_key, alg=alg)


class JWKSignatureVerifier(SignatureVerifier):
    def __init__(self, jwk: str):
        self._jwk: PyJWK = PyJWK.from_json(jwk)

    @override
    async def verify(self, token: str) -> dict[str, Any]:
        header = headers(token)
        alg = header.get("alg")

        return _decode(token, self._jwk, alg=alg)


class NoopSignatureVerifier(SignatureVerifier):
    @override
    async def verify(self, token: str) -> dict[str, Any]:
        return {}


def _decode(token: str, jwk: PyJWK, alg: str | None) -> dict[str, Any]:
    if not alg:
        raise InvalidTokenError("Token does not have a valid algorithm", capture=True)
    try:
        return decode(token, jwk, verify=True, algorithms=[alg])
    except JWTInvalidTokenError as e:
        raise InvalidTokenError("Invalid token signature", capture=False) from e
