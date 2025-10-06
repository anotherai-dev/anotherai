from typing import Annotated

from fastapi import Depends

from core.services.completion_runner import CompletionRunner
from core.services.payment_service import PaymentService
from core.services.store_completion.completion_storer import CompletionStorer
from protocol.api._dependencies._lifecycle import LifecycleDependenciesDep
from protocol.api._dependencies._tenant import TenantDep
from protocol.api._services.agent_service import AgentService
from protocol.api._services.annotation_service import AnnotationService
from protocol.api._services.completion_service import CompletionService
from protocol.api._services.deployment_service import DeploymentService
from protocol.api._services.experiment_service import ExperimentService
from protocol.api._services.files_service import FilesService
from protocol.api._services.organization_service import OrganizationService
from protocol.api._services.view_service import ViewService


def completion_runner(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> CompletionRunner:
    return CompletionRunner(
        tenant=tenant,
        completion_storage=dependencies.storage_builder.completions(tenant.uid),
        provider_factory=dependencies.provider_factory,
        event_router=dependencies.tenant_event_router(tenant.uid),
    )


CompletionRunnerDep = Annotated[CompletionRunner, Depends(completion_runner)]


def experiment_service(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> ExperimentService:
    return ExperimentService(
        experiment_storage=dependencies.storage_builder.experiments(tenant.uid),
        agent_storage=dependencies.storage_builder.agents(tenant.uid),
        completion_storage=dependencies.storage_builder.completions(tenant.uid),
        annotation_storage=dependencies.storage_builder.annotations(tenant.uid),
    )


ExperimentServiceDep = Annotated[ExperimentService, Depends(experiment_service)]


def completion_service(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> CompletionService:
    return CompletionService(
        completion_storage=dependencies.storage_builder.completions(tenant.uid),
        agent_storage=dependencies.storage_builder.agents(tenant.uid),
    )


CompletionServiceDep = Annotated[CompletionService, Depends(completion_service)]


def agent_service(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> AgentService:
    return AgentService(dependencies.storage_builder.agents(tenant.uid))


AgentServiceDep = Annotated[AgentService, Depends(agent_service)]


def annotation_service(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> AnnotationService:
    return AnnotationService(
        dependencies.storage_builder.annotations(tenant.uid),
        dependencies.storage_builder.experiments(tenant.uid),
        dependencies.storage_builder.completions(tenant.uid),
    )


AnnotationServiceDep = Annotated[AnnotationService, Depends(annotation_service)]


def view_service(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> ViewService:
    return ViewService(
        dependencies.storage_builder.views(tenant.uid),
        dependencies.storage_builder.completions(tenant.uid),
    )


ViewServiceDep = Annotated[ViewService, Depends(view_service)]


def organization_service(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> OrganizationService:
    return OrganizationService(dependencies.storage_builder.tenants(tenant.uid))


OrganizationServiceDep = Annotated[OrganizationService, Depends(organization_service)]


def deployment_service(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> DeploymentService:
    return DeploymentService(
        dependencies.storage_builder.deployments(tenant.uid),
        dependencies.storage_builder.completions(tenant.uid),
        agents_storage=dependencies.storage_builder.agents(tenant.uid),
    )


DeploymentServiceDep = Annotated[DeploymentService, Depends(deployment_service)]


def completion_storer(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> CompletionStorer:
    return CompletionStorer(
        completion_storage=dependencies.storage_builder.completions(tenant.uid),
        agent_storage=dependencies.storage_builder.agents(tenant.uid),
        file_storage=dependencies.storage_builder.files(tenant.uid),
    )


CompletionStorerDep = Annotated[CompletionStorer, Depends(completion_storer)]


def files_service(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> FilesService:
    return FilesService(dependencies.storage_builder.files(tenant.uid))


FilesServiceDep = Annotated[FilesService, Depends(files_service)]


def payment_service(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> PaymentService:
    return PaymentService(
        tenant_storage=dependencies.storage_builder.tenants(tenant.uid),
        payment_handler=dependencies.payment_handler(tenant.uid),
    )


PaymentServiceDep = Annotated[PaymentService, Depends(payment_service)]
