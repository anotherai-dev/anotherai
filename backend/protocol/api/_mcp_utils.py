import contextlib
import json
from typing import Any, override

from fastmcp.server import FastMCP
from fastmcp.server.auth import AccessToken, AuthProvider, RemoteAuthProvider, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult, default_serializer
from mcp.types import CallToolRequestParams
from pydantic import AnyHttpUrl, BaseModel, ValidationError
from structlog import get_logger

from core.consts import ANOTHERAI_API_URL, AUTHORIZATION_SERVER
from core.domain.exceptions import InvalidTokenError
from core.domain.tenant_data import TenantData
from core.services.documentation.documentation_search import DocumentationSearch
from protocol.api._dependencies._lifecycle import lifecyle_dependencies
from protocol.api._dependencies._services import completion_runner
from protocol.api._services.agent_service import AgentService
from protocol.api._services.annotation_service import AnnotationService
from protocol.api._services.completion_service import CompletionService
from protocol.api._services.deployment_service import DeploymentService
from protocol.api._services.documentation_service import DocumentationService
from protocol.api._services.experiment_service import ExperimentService
from protocol.api._services.organization_service import OrganizationService
from protocol.api._services.playground_service import PlaygroundService
from protocol.api._services.view_service import ViewService

_log = get_logger(__name__)


class BaseMiddleware(Middleware):
    @override
    async def on_call_tool(
        self,
        context: MiddlewareContext[CallToolRequestParams],
        call_next: CallNext[CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        # Trying to deserialize JSON sent as a string
        # See https://github.com/jlowin/fastmcp/issues/932
        if context.message.arguments:
            for k, arg in context.message.arguments.items():
                if isinstance(arg, str) and arg.startswith(("{", "[")):
                    with contextlib.suppress(json.JSONDecodeError):
                        context.message.arguments[k] = json.loads(arg)
        try:
            return await call_next(context)
        except ValidationError as e:
            _log.error(f"Validation error: {e}")
            raise e


def tool_serializer(value: Any) -> str:
    if isinstance(value, BaseModel):
        return value.model_dump_json(indent=2, exclude_none=True)
    return default_serializer(value)


class CustomFastMCP(FastMCP[Any]):
    @override
    def _setup_handlers(self) -> None:
        super()._setup_handlers()
        # Register call tool again to avoid validating input at the lowest level

        _ = self._mcp_server.call_tool(validate_input=False)(self._mcp_call_tool)


_CLAIMS_TENANT = "tenant"


# Stupid hack to allow testing
# TODO: figure out how to avoid wrapping in an async function
async def _async_get_access_token() -> AccessToken | None:
    return get_access_token()


async def _authenticated_tenant() -> TenantData:
    token = await _async_get_access_token()
    if not token or not token.claims:
        raise InvalidTokenError("No token found")
    return token.claims[_CLAIMS_TENANT]


async def playground_service() -> PlaygroundService:
    deps = lifecyle_dependencies()
    tenant = await _authenticated_tenant()
    return PlaygroundService(
        completion_runner(tenant, deps),
        deps.storage_builder.agents(tenant.uid),
        deps.storage_builder.experiments(tenant.uid),
        deps.storage_builder.completions(tenant.uid),
    )


async def experiment_service() -> ExperimentService:
    deps = lifecyle_dependencies()
    tenant = await _authenticated_tenant()
    return ExperimentService(
        deps.storage_builder.experiments(tenant.uid),
        deps.storage_builder.agents(tenant.uid),
        deps.storage_builder.completions(tenant.uid),
        deps.storage_builder.annotations(tenant.uid),
    )


async def annotation_service() -> AnnotationService:
    deps = lifecyle_dependencies()
    tenant = await _authenticated_tenant()
    return AnnotationService(
        deps.storage_builder.annotations(tenant.uid),
        deps.storage_builder.experiments(tenant.uid),
        deps.storage_builder.completions(tenant.uid),
    )


def documentation_service() -> DocumentationService:
    return DocumentationService(DocumentationSearch())


async def agent_service() -> AgentService:
    deps = lifecyle_dependencies()
    tenant = await _authenticated_tenant()
    return AgentService(deps.storage_builder.agents(tenant.uid))


async def completion_service() -> CompletionService:
    deps = lifecyle_dependencies()
    tenant = await _authenticated_tenant()
    return CompletionService(deps.storage_builder.completions(tenant.uid), deps.storage_builder.agents(tenant.uid))


async def view_service() -> ViewService:
    deps = lifecyle_dependencies()
    tenant = await _authenticated_tenant()
    return ViewService(deps.storage_builder.views(tenant.uid), deps.storage_builder.completions(tenant.uid))


async def organization_service() -> OrganizationService:
    deps = lifecyle_dependencies()
    tenant = await _authenticated_tenant()
    return OrganizationService(deps.storage_builder.tenants(tenant.uid))


async def deployment_service() -> DeploymentService:
    deps = lifecyle_dependencies()
    tenant = await _authenticated_tenant()
    return DeploymentService(deps.storage_builder.deployments(tenant.uid), deps.storage_builder.completions(tenant.uid))


class CustomTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        deps = lifecyle_dependencies()
        tenant = await deps.security_service.find_tenant(token)
        return AccessToken(
            token=token,
            client_id="",
            scopes=[],
            claims={
                _CLAIMS_TENANT: tenant,
            },
        )


def build_auth_provider() -> AuthProvider:
    return RemoteAuthProvider(
        token_verifier=CustomTokenVerifier(),
        authorization_servers=[AnyHttpUrl(AUTHORIZATION_SERVER)],
        resource_server_url=f"{ANOTHERAI_API_URL}/mcp",
    )
