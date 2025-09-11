import io
import json
from typing import Any
from unittest.mock import Mock, patch

import pytest

from core.domain.exceptions import InvalidTokenError
from core.utils.signature_verifier import JWKSetSignatureVerifier, JWKSignatureVerifier

_JWKS = {
    "keys": [
        {
            "kty": "RSA",
            "e": "AQAB",
            "use": "sig",
            "kid": "1",
            "alg": "RS256",
            "n": "xO3RFnVFNpT9QDAuvhqTBmc4ctMueyHPzcv4RnoJ6pezENRznrrskTtTtD5zZcpEAQzkm_n1qlJmxB4ur84IaleVqbd1kiJD5zu70Q3ClQ6qf6d3XWgW_L317AKXmIoWr5ygtHIVXg2-0fNdvAmhymq9chws3RA36zPiEaGyEKJiTasixFH94yxpnnd8nYUp299OX-Zn760cZ85-B6dptK-75NuQZhBwl8DtSLMnbk615o87QqUO8IsyNvUHMri_4PQ4AndHsXlgunRx8__SZBYbAmCMrbI3317yumMshIOrD5QK6qn1Z9IRjlsh4npEQhjtMERWt8GgY15bMRDvQQ",
        },
    ],
}
# JWT above Corresponds to private key. Test private key, do not use in production.
# -----BEGIN PRIVATE KEY-----
# MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDE7dEWdUU2lP1A
# MC6+GpMGZzhy0y57Ic/Ny/hGegnql7MQ1HOeuuyRO1O0PnNlykQBDOSb+fWqUmbE
# Hi6vzghqV5Wpt3WSIkPnO7vRDcKVDqp/p3ddaBb8vfXsApeYihavnKC0chVeDb7R
# 8128CaHKar1yHCzdEDfrM+IRobIQomJNqyLEUf3jLGmed3ydhSnb305f5mfvrRxn
# zn4Hp2m0r7vk25BmEHCXwO1IsyduTrXmjztCpQ7wizI29QcyuL/g9DgCd0exeWC6
# dHHz/9JkFhsCYIytsjffXvK6YyyEg6sPlArqqfVn0hGOWyHiekRCGO0wRFa3waBj
# XlsxEO9BAgMBAAECggEAdF5v6sx7jOh3yqFuTaoYbXU7dybx1ZNCX8MDQGpHR9hC
# 2VQhyo980cl0ChPJT0I580DyKnWHxRESZxvKzNp8QJLm/rZJhIQ5CgBTWRK/hCN5
# fxuvvoOO6eU62C8j8+DNzRJKKLcthzmqJBiisEYk1B9FOZQKssstsBAlq/OX7Jlt
# feDEAQ5zvaDEe7f6jAbHzLXBArV1ROhNXjZKcM2akBW0dngWfpgtjLWaJK1NS/K+
# X5VCakEKglGjHxfZ6KM8dyB5KWOzWcG985XXxF2x1No5kvu7mp/7ZEKkOy2q/tOM
# FK5zAWtgXS0Kf1OOdn4rwNHo2psZvBlnd1zJOdUQ0QKBgQD6So7okOujiAdKCpbK
# xho/C65mRDvYQbS63UTdopgLu9OEWWvcNh7P9AdWM95O2v9ywjeSHd2YH35AsRAf
# S1sody1AY+C5e1f1OeCe8rjxdJtWUgHAUlZAaIiANNBjZzIZJp0j+80GJwqbvbV9
# ieWoN0CDIgKmiR7eoljKBsLCnQKBgQDJa62XHFwRjIBW1J+Pl9SNW+/0eRgdee+q
# rnsABRO77x1g4NGktuj5O4f+VWYMt2bpfWm9d5j3427cKqvRk8onKPaAJPwL28Ju
# RsVkowQ35C6bfC+cCg3q+BBOAdsP8rKtTvqXvduYF3LKQpipHJ0VGSVVsu2OQ1T5
# tl05LVS79QKBgEybY3BFYwoziV+dLBg2WDQxxBhjDBodyk5jiT95E6aLv6rDn+LP
# 4dBudYxp5cIm/4bFcTLU101HXmI4j6G0c9tH1t7dcxvyZ7KUG28rBXZJ5X2fLhAK
# Y4HlPNpYz+uM22WdTv2DhXY7nuCaSSF6goNhHerFDyCf2YX1FM4JEbV1AoGBAKlu
# y8p2j7gvYXIpT8PBq4nx0YrsJm39Oa9xMISWwL/xZ9wrog6V0qp8+mvmuH5v9MDq
# v30i0umLRqErv/b/BCkm2xx2gBMVnJuZKsj6HD1L1Cz1LTNsfcKvQz/rbbQfq1AA
# ROpKSiPJbcVYegSfzj+GNJK/ffeTCjM4xXioekPVAoGARKi2xJMVKeXCh1jtWVtn
# 8wTM7PT8K28yAf8kknjnC3+lFLnwOUhkhH3XjfDEwYPXnAxm6zB99JNkQfDYyC+p
# xFgaiRPYOTgpSMyTD1vY3yjJUgoNl1N8aw0yoLa3VS8TRiKo0yIEyDU96y/KQDN1
# ayRIg49HYtsurtyfnan9wuc=
# -----END PRIVATE KEY-----

# use jwt.io encoder to generate the jwt

_TEST_JWT = "eyJraWQiOiIxIiwiYWxnIjoiUlMyNTYifQ.eyJleHAiOjE5NTQ5ODk5MjJ9.SlqjJ846bwXFFZ0-4QlFYnwbvE-vXqClGoOV_h4beMdVEXbW0Z6gFAMHIfLw4y0Oe0WfMHdhbUTyUiRUtB5rhh67VceQqJB2BawoeSFI1dRmOcOz1tTwnC_eTZoGBV1yR8Hn1CmipZtmyN0CqgsAjeOuvsXIHxkz0XdMGyXQtsnkcMK-vrfYOxEelktEd1CCvIHf0BgOWWfj9imDnMFjbWM-hwTMqSiXFdPCU4R6qK1aFV3vICbDkArfXTpQHP4FHGBSrbliwikRhN9aDoYfyINhRSnL2Q1xLcsO_PgoGiVTfX0Z7aBuE0LPojkR6W2zFIYhF7IX2TNKvr-THAAGaA"


class TestJWKSignatureVerifier:
    @pytest.fixture
    def jwk_verifier(self):
        payload = json.dumps(_JWKS["keys"][0])
        return JWKSignatureVerifier(payload)

    async def test_verify(self, jwk_verifier: JWKSignatureVerifier):
        payload = await jwk_verifier.verify(_TEST_JWT)
        assert payload == {"exp": 1954989922}

    @pytest.mark.parametrize(
        ("invalid_token", "expected_message"),
        [
            pytest.param("", "Invalid bearer token. Provide either an API key (aai-***) or a JWT", id="empty"),
            pytest.param("abc.def.ghi", "Token does not have a valid header", id="not-base64"),  # not base64
            pytest.param(
                "eyJhbGciOiJSUzI1NiJ9..",
                "Invalid token signature",
                id="missing-payload-signature",
            ),  # missing payload/signature
            pytest.param(
                "eyJraWQiOiIxIn0.e30.signature",
                "Token does not have a valid algorithm",
                id="missing-alg",
            ),  # missing alg
            pytest.param(
                "eyJraWQiOiIxIiwiYWxnIjoiUlMyNTYifQ.e30.invalidsig",
                "Invalid token signature",
                id="invalid-signature",
            ),  # invalid signature, but header is valid
        ],
    )
    async def test_jwk_invalid_token(
        self,
        jwk_verifier: JWKSetSignatureVerifier,
        invalid_token: str,
        expected_message: str,
    ):
        with pytest.raises(InvalidTokenError) as exc:
            _ = await jwk_verifier.verify(invalid_token)
        assert expected_message in str(exc.value)


class TestJWKSetSignatureVerifier:
    @pytest.fixture
    def jwk_verifier(self):
        return JWKSetSignatureVerifier("http://localhost:8000/.well-known/jwks.json")

    @pytest.fixture
    def mock_urlopen(self):
        def _side_effect(*args: Any, **kwargs: Any):
            return io.StringIO(json.dumps(_JWKS))

        with patch("urllib.request.urlopen", side_effect=_side_effect) as mock:
            yield mock

    async def test_verify(self, jwk_verifier: JWKSetSignatureVerifier, mock_urlopen: Mock):
        payload = await jwk_verifier.verify(_TEST_JWT)

        assert mock_urlopen.call_count == 1
        assert mock_urlopen.call_args[0][0].full_url == "http://localhost:8000/.well-known/jwks.json"
        assert payload == {"exp": 1954989922}

    @pytest.mark.parametrize(
        ("invalid_token", "expected_message"),
        [
            pytest.param("", "Invalid bearer token. Provide either an API key (aai-***) or a JWT", id="empty"),
            pytest.param("abc.def.ghi", "Token does not have a valid header", id="not-base64"),  # not base64
            pytest.param(
                "eyJhbGciOiJSUzI1NiJ9..",
                "Token does not have a valid kid",
                id="missing-payload-signature",
            ),  # missing payload/signature
            pytest.param(
                "eyJhbGciOiJSUzI1NiJ9.e30.signature",
                "Token does not have a valid kid",
                id="missing-kid",
            ),  # missing kid
            pytest.param(
                "eyJraWQiOiIxIn0.e30.signature",
                "Token does not have a valid algorithm",
                id="missing-alg",
            ),  # missing alg
            pytest.param(
                "eyJraWQiOiIxIiwiYWxnIjoiUlMyNTYifQ.e30.invalidsig",
                "Invalid token signature",
                id="invalid-signature",
            ),  # invalid signature, but header is valid
        ],
    )
    async def test_jwkset_invalid_token(
        self,
        jwk_verifier: JWKSetSignatureVerifier,
        mock_urlopen: Mock,
        invalid_token: str,
        expected_message: str,
    ):
        with pytest.raises(InvalidTokenError) as exc:
            _ = await jwk_verifier.verify(invalid_token)
        assert expected_message in str(exc.value)
