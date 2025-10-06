from typing import Annotated

from taskiq import Context, TaskiqDepends

from core.domain.events import Event, EventRouter
from core.domain.tenant_data import TenantData
from core.services.completion_runner import CompletionRunner
from core.services.payment_service import PaymentService
from core.services.store_completion.completion_storer import CompletionStorer
from core.storage.agent_storage import AgentStorage
from core.storage.completion_storage import CompletionStorage
from core.storage.user_storage import UserStorage
from protocol._common.lifecycle import LifecycleDependencies
from protocol.api._services.playground_service import PlaygroundService


def _event_dep(context: Annotated[Context, TaskiqDepends()]) -> Event:
    event = context.message.args[0]
    if not isinstance(event, Event):
        raise ValueError("Event dependency must be an Event")
    if not event.tenant_uid:
        raise ValueError("Event must have a tenant_uid")
    return event


EventDep = Annotated[Event, TaskiqDepends(_event_dep)]


def _lifecycle_dependencies(context: Annotated[Context, TaskiqDepends()]) -> LifecycleDependencies:
    return context.state.dependencies


LifecycleDependenciesDep = Annotated[LifecycleDependencies, TaskiqDepends(_lifecycle_dependencies)]


def _event_router(event: EventDep, dependencies: LifecycleDependenciesDep) -> EventRouter:
    return dependencies.tenant_event_router(event.tenant_uid)


EventRouterDep = Annotated[EventRouter, TaskiqDepends(_event_router)]


async def _tenant_data(
    context: Annotated[Context, TaskiqDepends()],
    event: EventDep,
    dependencies: LifecycleDependenciesDep,
) -> TenantData:
    tenant_storage = dependencies.storage_builder.tenants(-1)
    return await tenant_storage.tenant_by_uid(event.tenant_uid)


TenantDataDep = Annotated[TenantData, TaskiqDepends(_tenant_data)]


def _completion_storage(event: EventDep, dependencies: LifecycleDependenciesDep) -> CompletionStorage:
    return dependencies.storage_builder.completions(event.tenant_uid)


CompletionStorageDep = Annotated[CompletionStorage, TaskiqDepends(_completion_storage)]


def _agent_storage(event: EventDep, dependencies: LifecycleDependenciesDep) -> AgentStorage:
    return dependencies.storage_builder.agents(event.tenant_uid)


AgentStorageDep = Annotated[AgentStorage, TaskiqDepends(_agent_storage)]


def _completion_storer(
    event: EventDep,
    dependencies: LifecycleDependenciesDep,
    completion_storage: CompletionStorageDep,
    agent_storage: AgentStorageDep,
) -> CompletionStorer:
    return CompletionStorer(
        completion_storage=completion_storage,
        agent_storage=agent_storage,
        file_storage=dependencies.storage_builder.files(event.tenant_uid),
    )


CompletionStorerDep = Annotated[CompletionStorer, TaskiqDepends(_completion_storer)]


def _payment_service(event: EventDep, dependencies: LifecycleDependenciesDep) -> PaymentService:
    return PaymentService(
        tenant_storage=dependencies.storage_builder.tenants(event.tenant_uid),
        payment_handler=dependencies.payment_handler(event.tenant_uid),
    )


PaymentServiceDep = Annotated[PaymentService, TaskiqDepends(_payment_service)]


def _user_storage(event: EventDep, dependencies: LifecycleDependenciesDep) -> UserStorage:
    return dependencies.storage_builder.users(event.tenant_uid)


UserStorageDep = Annotated[UserStorage, TaskiqDepends(_user_storage)]


def _completion_runner(
    event: EventDep,
    event_router: EventRouterDep,
    tenant: TenantDataDep,
    completion_storage: CompletionStorageDep,
    agent_storage: AgentStorageDep,
    dependencies: LifecycleDependenciesDep,
) -> CompletionRunner:
    return CompletionRunner(
        tenant=tenant,
        completion_storage=completion_storage,
        provider_factory=dependencies.provider_factory,
        event_router=event_router,
    )


CompletionRunnerDep = Annotated[CompletionRunner, TaskiqDepends(_completion_runner)]


def _playground_service(
    event: EventDep,
    event_router: EventRouterDep,
    tenant: TenantDataDep,
    completion_storage: CompletionStorageDep,
    agent_storage: AgentStorageDep,
    dependencies: LifecycleDependenciesDep,
    completion_runner: CompletionRunnerDep,
) -> PlaygroundService:
    return PlaygroundService(
        completion_runner=completion_runner,
        completion_storage=completion_storage,
        agent_storage=agent_storage,
        event_router=event_router,
        deployment_storage=dependencies.storage_builder.deployments(event.tenant_uid),
        experiment_storage=dependencies.storage_builder.experiments(event.tenant_uid),
    )


PlaygroundServiceDep = Annotated[PlaygroundService, TaskiqDepends(_playground_service)]
