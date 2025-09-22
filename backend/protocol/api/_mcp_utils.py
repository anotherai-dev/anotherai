import contextlib
import json
from typing import Any, override

import pydantic_core
from fastmcp.exceptions import ToolError
from fastmcp.server import FastMCP
from fastmcp.server.auth import AccessToken, AuthProvider, TokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import Tool, ToolResult, default_serializer
from mcp.types import CallToolRequestParams, ListToolsRequest
from pydantic import BaseModel, ValidationError
from structlog import get_logger
from structlog.contextvars import bind_contextvars
from transformers import AutoTokenizer

from core.domain.exceptions import DefaultError, InvalidTokenError
from core.domain.tenant_data import TenantData
from core.providers._base.provider_error import ProviderError
from core.services.documentation.documentation_search import DocumentationSearch
from protocol.api._api_models import ChunkedResponse
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
        _log.info("on_call_tool", method=context.method)
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
            _log.error("Validation error", exc_info=e)
            raise e

    @override
    async def on_list_tools(
        self,
        context: MiddlewareContext[ListToolsRequest],
        call_next: CallNext[ListToolsRequest, list[Tool]],
    ) -> list[Tool]:
        all_tools = await call_next(context)
        # Some LLMs are hellbent on sending objects as stringified JSON. So we add strings as an acceptable type
        # For array and objects
        for tool in all_tools:
            if tool.parameters:
                tool.parameters = _add_string_as_acceptable_type(tool.parameters)

        return all_tools

    async def on_message(self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]) -> Any:
        tool_name = getattr(context.message, "name", None)
        bind_contextvars(tool_name=tool_name)
        _log.debug("on_message", method=context.method)
        try:
            return await call_next(context)
        except ToolError as e:
            cause = e.__cause__
            if isinstance(cause, (ProviderError, DefaultError)):
                if cause.capture:
                    _log.exception("Error in message", exc_info=e)
                # We can re-raise the original error as is. FastMCP will handle the formatting
                raise e
            if isinstance(cause, ValidationError):
                # Tracking of when
                _log.error("Validation error in message", exc_info=e)
                raise e
            # Anything else should not permeate to the outside so we raise an opaque error
            _log.exception("Unknown Error in message", exc_info=e)
            raise Exception("An unknown error occurred") from None

        except Exception as e:  # noqa: BLE001
            # That would be unexpected
            _log.exception("Unknown Error in message not wrapped in tool error", exc_info=e)
            raise Exception("An unknown error occurred") from None


def _add_string_to_property_type(property: dict[str, Any]) -> dict[str, Any]:
    if (t := property.get("type")) and isinstance(t, str) and t in {"array", "object"}:
        return {
            **property,
            "type": [t, "string"],
        }
    if (
        (any_of := property.get("anyOf"))
        and isinstance(any_of, list)
        and not any(item.get("type") == "string" for item in any_of)
    ):
        return {
            **property,
            "anyOf": [
                *any_of,
                {
                    "type": "string",
                },
            ],
        }
    return property


def _add_string_as_acceptable_type(parameters: dict[str, Any]) -> dict[str, Any]:
    # We only add to root level
    properties: dict[str, Any] = parameters.get("properties", {})
    if not properties or not isinstance(properties, dict):
        return parameters

    new_properties = {k: _add_string_to_property_type(v) for k, v in properties.items()}

    return {
        **parameters,
        "properties": new_properties,
    }


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
        deps.storage_builder.deployments(tenant.uid),
        deps.tenant_event_router(tenant.uid),
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
        bind_contextvars(
            tenant_org_id=tenant.org_id,
            tenant_owner_id=tenant.owner_id,
            tenant_slug=tenant.slug,
        )
        return AccessToken(
            token=token,
            client_id="",
            scopes=[],
            claims={
                _CLAIMS_TENANT: tenant,
            },
        )


def build_auth_provider() -> AuthProvider:
    return CustomTokenVerifier()


def chunk[T](payload: T, chunk_offset: int | None, max_chunk_token_size: int | None) -> T | ChunkedResponse:
    if max_chunk_token_size is None:
        return payload
    if chunk_offset is None:
        chunk_offset = 0

    tok = AutoTokenizer.from_pretrained("bert-base-uncased", use_fast=True)
    # We pretty print the JSON. We could use custom separators as well
    # TODO: we should store the splits in a redis to make sure
    # We don't return bogus data
    serialized = pydantic_core.to_json(payload, indent=2).decode("utf-8")
    lines = serialized.splitlines()[chunk_offset:]
    total_token_count = 0

    for idx, line in enumerate(lines):
        line_count = len(tok.encode(line))
        total_token_count += line_count
        if total_token_count > max_chunk_token_size:
            return ChunkedResponse(chunk="\n".join(lines[:idx]), next_chunk_offset=chunk_offset + len(line))

    return ChunkedResponse(chunk="\n".join(lines), next_chunk_offset=None)
