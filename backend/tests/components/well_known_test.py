import pytest

from tests.components._common import IntegrationTestClient


# MCP clients try to access the well-known routes from a variety of URLs
@pytest.mark.parametrize(
    "url",
    [
        "/.well-known/oauth-protected-resource",
        "/.well-known/oauth-protected-resource/mcp",
        "/mcp/.well-known/oauth-protected-resource",
    ],
)
async def test_oauth_protected_resource(test_api_client: IntegrationTestClient, url: str):
    res = await test_api_client.client.get(url)
    assert res.status_code == 200
    assert res.json() == {
        "resource": "http://localhost:8000/mcp",
        "authorization_servers": ["http://auth.localhost:8000"],
        "scopes_supported": ["openid", "email", "profile"],
        "resource_name": "Another AI",
        "resource_documentation": "http://localhost:8000/mcp",
        "bearer_methods_supported": ["header"],
    }


@pytest.mark.parametrize(
    "url",
    [
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-authorization-server/mcp",
        "/mcp/.well-known/oauth-authorization-server",
    ],
)
async def test_oauth_authorization_server(test_api_client: IntegrationTestClient, url: str):
    res = await test_api_client.client.get(url)
    assert res.status_code == 307
