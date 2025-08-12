import contextlib
import json
from typing import Any, override

from fastmcp.server import FastMCP
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import default_serializer
from mcp.types import CallToolRequestParams, CallToolResult
from pydantic import BaseModel, ValidationError
from structlog import get_logger

from core.domain.tenant_data import TenantData
from core.services.documentation_search import DocumentationSearch
from protocol.api._dependencies._lifecycle import lifecyle_dependencies
from protocol.api._dependencies._services import completion_runner
from protocol.api._dependencies._tenant import authenticated_tenant
from protocol.api._services.agent_service import AgentService
from protocol.api._services.annotation_service import AnnotationService
from protocol.api._services.completion_service import CompletionService
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
        call_next: CallNext[CallToolRequestParams, CallToolResult],
    ) -> CallToolResult:
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


async def _authenticated_tenant() -> TenantData:
    request = get_http_request()
    lifecycle = lifecyle_dependencies()
    return await authenticated_tenant(request, lifecycle)


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
