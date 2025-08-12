import os
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from structlog import get_logger

from core.domain.exceptions import DefaultError
from core.logs.setup_logs import setup_logs
from core.providers._base.provider_error import ProviderError
from protocol._common import probes_router
from protocol._common.lifecycle import shutdown, startup
from protocol.api import api_router, run_router
from protocol.api._api_utils import convert_error_response
from protocol.api._dependencies._misc import set_start_time
from protocol.api._mcp import mcp

setup_logs()

_log = get_logger(__name__)

# TODO: investigate why stateless_http is needed
_mcp_app = mcp.http_app(transport="streamable-http", path="/mcp", stateless_http=True)


# Separate function to allow patching in tests
@asynccontextmanager
async def _mcp_lifespan(app: FastAPI):
    async with _mcp_app.lifespan(app):
        yield


@asynccontextmanager
async def _lifespan(app: FastAPI):
    dependencies = await startup()
    app.state.dependencies = dependencies

    if os.getenv("MIGRATE_STORAGE_ON_STARTUP") == "1":
        _log.info("Migrating storage on startup")
        await dependencies.storage_builder.migrate()
        _log.info("Storage migrated")

    async with _mcp_lifespan(app):
        yield

    await shutdown(dependencies)


api = FastAPI(title="Another AI", lifespan=_lifespan)

# Add CORS middleware to allow requests from the web app
if origins := os.environ.get("ALLOWED_ORIGINS", "*"):
    api.add_middleware(
        CORSMiddleware,
        allow_origins=origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@api.middleware("http")
async def middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    _ = set_start_time(request)
    response = await call_next(request)
    return response


@api.exception_handler(ProviderError)
async def provider_error_handler(request: Request, exc: ProviderError):
    exc.capture_if_needed()
    retry_after = exc.retry_after_str()
    headers = {"Retry-After": retry_after} if retry_after else None
    return convert_error_response(exc.serialized(), headers=headers)


@api.exception_handler(DefaultError)
async def default_error_handler(request: Request, exc: DefaultError):
    return convert_error_response(exc.serialized())


api.include_router(probes_router.router)

# TODO: split when we have separate containers
api.include_router(api_router.router)
api.include_router(run_router.router)


api.mount("/", _mcp_app)

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv

    _ = load_dotenv(override=True)
    uvicorn.run(api, port=8000)
