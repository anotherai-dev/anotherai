from typing import Annotated, Any

from fastapi import APIRouter, Body, Query

from protocol.api._api_models import (
    Agent,
    Annotation,
    APIKey,
    CompleteAPIKey,
    Completion,
    CreateAPIKeyRequest,
    CreateExperimentRequest,
    CreateViewRequest,
    Deployment,
    Experiment,
    Model,
    Page,
    PatchViewFolderRequest,
    PatchViewRequest,
    View,
    ViewFolder,
)
from protocol.api._dependencies._services import (
    AgentServiceDep,
    AnnotationServiceDep,
    CompletionServiceDep,
    ExperimentServiceDep,
    OrganizationServiceDep,
    ViewServiceDep,
)
from protocol.api._services import models_service

router = APIRouter(prefix="")

# ------------------------------------------------------------
# Models


@router.get("/v1/models", response_model_exclude_none=True)
async def list_models() -> list[Model]:
    return await models_service.list_models()


# ------------------------------------------------------------
# Agents


@router.get("/v1/agents", response_model_exclude_none=True)
async def list_agents(
    agent_service: AgentServiceDep,
) -> Page[Agent]:
    return await agent_service.list_agents()


# ------------------------------------------------------------
# Experiments


@router.get("/v1/experiments", response_model_exclude_none=True)
async def list_experiments(
    experiment_service: ExperimentServiceDep,
    agent_id: Annotated[str | None, Query(description="The agent id to filter experiments by")] = None,
    limit: Annotated[int, Query(description="Maximum number of experiments to return", ge=1, le=100)] = 10,
    offset: Annotated[int, Query(description="Number of experiments to skip", ge=0)] = 0,
) -> Page[Experiment]:
    return await experiment_service.list_experiments(agent_id, limit, offset)


@router.post("/v1/experiments", response_model_exclude_none=True)
async def create_experiment(
    experiment_service: ExperimentServiceDep,
    body: CreateExperimentRequest,
) -> Experiment:
    return await experiment_service.create_experiment(body)


@router.get("/v1/experiments/{experiment_id}", response_model_exclude_none=True)
async def get_experiment(
    experiment_service: ExperimentServiceDep,
    experiment_id: str,
) -> Experiment:
    return await experiment_service.get_experiment(experiment_id)


# ------------------------------------------------------------
# Completions


@router.get("/v1/completions/query")
async def query_completions(
    completion_service: CompletionServiceDep,
    query: Annotated[str, Query(description="A SQL Query on the 'completions' table")],
) -> list[dict[str, Any]]:
    return (await completion_service.query_completions(query)).rows


@router.get("/v1/completions/{completion_id}", response_model_exclude_none=True)
async def get_completion(
    completion_service: CompletionServiceDep,
    completion_id: str,
) -> Completion:
    return await completion_service.get_completion(completion_id)


# ------------------------------------------------------------
# Annotations


@router.get("/v1/annotations", response_model_exclude_none=True)
async def get_annotations(
    annotation_service: AnnotationServiceDep,
    experiment_id: Annotated[str | None, Query(description="Filter by experiment ID")] = None,
    completion_id: Annotated[str | None, Query(description="Filter by run ID")] = None,
    since: Annotated[str | None, Query(description="Filter by timestamp (ISO format)")] = None,
    limit: Annotated[int, Query(description="Maximum number of annotations to return", ge=1, le=1000)] = 100,
) -> Page[Annotation]:
    return await annotation_service.get_annotations(
        experiment_id=experiment_id,
        completion_id=completion_id,
        since=since,
        limit=limit,
    )


@router.post("/v1/annotations")
async def add_annotations(
    annotation_service: AnnotationServiceDep,
    annotations: Annotated[list[Annotation], Body(description="List of annotations to add")],
) -> None:
    """Creates annotations for a given experiment or completion.
    When creating an annotation that targets a completion within the context of an experiment,
    the completion is automatically added to the experiment.
    """
    await annotation_service.add_annotations(annotations)


@router.delete("/v1/annotations/{annotation_id}")
async def delete_annotation(
    annotation_service: AnnotationServiceDep,
    annotation_id: str,
) -> None:
    await annotation_service.delete_annotation(annotation_id)


# ------------------------------------------------------------
# Dashboards


@router.post("/v1/views", response_model_exclude_none=True)
async def create_view(
    view_service: ViewServiceDep,
    view: CreateViewRequest,
) -> View:
    return await view_service.create_view(view)


@router.get("/v1/views", response_model_exclude_none=True)
async def list_views(
    view_service: ViewServiceDep,
) -> Page[ViewFolder]:
    return await view_service.list_view_folders()


@router.get("/v1/views/{view_id}", response_model_exclude_none=True)
async def get_view(
    view_service: ViewServiceDep,
    view_id: str,
) -> View:
    return await view_service.get_view(view_id)


@router.patch("/v1/views/{view_id}", response_model_exclude_none=True)
async def patch_view(
    view_service: ViewServiceDep,
    view_id: str,
    view: PatchViewRequest,
) -> View:
    return await view_service.patch_view(view_id, view)


@router.delete("/v1/views/{view_id}")
async def delete_view(
    view_service: ViewServiceDep,
    view_id: str,
) -> None:
    await view_service.delete_view(view_id)


@router.post("/v1/view-folders", response_model_exclude_none=True)
async def create_view_folder(
    view_service: ViewServiceDep,
    view_folder: ViewFolder,
) -> ViewFolder:
    return await view_service.create_view_folder(view_folder)


@router.patch("v1/view-folders/{view_folder_id}", response_model_exclude_none=True)
async def patch_view_folder(
    view_service: ViewServiceDep,
    view_folder_id: str,
    view_folder: PatchViewFolderRequest,
) -> None:
    await view_service.patch_view_folder(view_folder_id, view_folder)


@router.delete("v1/view-folders/{view_folder_id}")
async def delete_view_folder(
    view_service: ViewServiceDep,
    view_folder_id: str,
) -> None:
    await view_service.delete_view_folder(view_folder_id)


# ------------------------------------------------------------
# API Keys


@router.get("/v1/organization/keys")
async def list_api_keys(
    organization_service: OrganizationServiceDep,
) -> Page[APIKey]:
    return await organization_service.list_api_keys()


@router.post("/v1/organization/keys")
async def create_api_key(
    organization_service: OrganizationServiceDep,
    request: CreateAPIKeyRequest,
) -> CompleteAPIKey:
    return await organization_service.create_api_key(request)


@router.delete("/v1/organization/keys/{key_id}")
async def delete_api_key(
    organization_service: OrganizationServiceDep,
    key_id: str,
) -> None:
    await organization_service.delete_api_key(key_id)


# ------------------------------------------------------------
# Deployments


@router.get("/v1//deployments", response_model_exclude_none=True)
async def list_deployments() -> Page[Deployment]:
    raise NotImplementedError


@router.post("/v1/deployments", response_model_exclude_none=True)
async def create_deployment(deployment: Deployment) -> Deployment:
    raise NotImplementedError


@router.patch("/v1/deployments/{deployment_id}", response_model_exclude_none=True)
async def patch_deployment(deployment_id: str, deployment: Deployment) -> Deployment:
    raise NotImplementedError


@router.delete("/v1/deployments/{deployment_id}")
async def archive_deployment(deployment_id: str) -> None:
    """Archives a deployment. The deployment can still be used if referred to by ID but no longer
    appears in the list of deployments."""
    raise NotImplementedError
