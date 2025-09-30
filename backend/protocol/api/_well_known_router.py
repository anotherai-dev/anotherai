from fastapi import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse

from core.consts import ANOTHERAI_API_URL, AUTHORIZATION_SERVER

router = APIRouter(prefix="/.well-known", include_in_schema=False)


@router.get("/oauth-protected-resource/mcp")
@router.options("/oauth-protected-resource")
@router.get("/oauth-protected-resource")
async def oauth_protected_resource():
    return JSONResponse(
        {
            "resource": f"{ANOTHERAI_API_URL}/mcp",
            "authorization_servers": [AUTHORIZATION_SERVER],
            "scopes_supported": ["openid", "email", "profile"],
            "resource_name": "Another AI",
            "resource_documentation": f"{ANOTHERAI_API_URL}/mcp",
            "bearer_methods_supported": ["header"],
        },
    )


@router.options("/oauth-authorization-server")
@router.get("/oauth-authorization-server")
@router.get("/oauth-authorization-server/mcp")
async def oauth_authorization_server():
    return RedirectResponse(f"{AUTHORIZATION_SERVER}/.well-known/oauth-authorization-server")
