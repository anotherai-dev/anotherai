from fastapi import APIRouter

from protocol.api._dependencies._lifecycle import LifecycleDependenciesDep
from protocol.api._dependencies._misc import RequestStartDep
from protocol.api._dependencies._services import CompletionRunnerDep
from protocol.api._dependencies._tenant import TenantWithCreditsDep
from protocol.api._run_models import OpenAIProxyChatCompletionRequest
from protocol.api._services.run.run_service import RunService

router = APIRouter(prefix="")


# We alias the completion route to account for trailing slashes in the openai
# base URL. It seems that some SDKs require the trailing slash, and some don't...
@router.post("/v1chat/completions", include_in_schema=False)
@router.post("/v1//chat/completions", include_in_schema=False)
@router.post("/v1/chat/completions")
async def chat_completions(
    request: OpenAIProxyChatCompletionRequest,
    completion_runner: CompletionRunnerDep,
    dependencies: LifecycleDependenciesDep,
    start_time: RequestStartDep,
    tenant: TenantWithCreditsDep,
):
    run_service = RunService(tenant, completion_runner, dependencies.storage_builder.deployments(tenant.uid))
    return await run_service.run(request, start_time)
