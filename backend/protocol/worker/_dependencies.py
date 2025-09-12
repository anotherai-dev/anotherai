from typing import Annotated

from taskiq import Context, TaskiqDepends

from core.domain.events import Event
from core.services.payment_service import PaymentService
from core.services.store_completion.completion_storer import CompletionStorer
from core.storage.user_storage import UserStorage
from protocol._common.lifecycle import LifecycleDependencies


def _event_dep(context: Annotated[Context, TaskiqDepends()]) -> Event:
    event = context.message.args[0]
    if not isinstance(event, Event):
        raise ValueError("Event dependency must be an Event")
    if not event.tenant_uid:
        raise ValueError("Event must have a tenant_uid")
    return event


EventDep = Annotated[Event, TaskiqDepends(_event_dep)]


def _lifecyle_dependencies(context: Annotated[Context, TaskiqDepends()]) -> LifecycleDependencies:
    return context.state.dependencies


LifecycleDependenciesDep = Annotated[LifecycleDependencies, TaskiqDepends(_lifecyle_dependencies)]


def _completion_storer(event: EventDep, dependencies: LifecycleDependenciesDep) -> CompletionStorer:
    return CompletionStorer(
        completion_storage=dependencies.storage_builder.completions(event.tenant_uid),
        agent_storage=dependencies.storage_builder.agents(event.tenant_uid),
        file_storage=dependencies.storage_builder.files(event.tenant_uid),
    )


CompletionStorerDep = Annotated[CompletionStorer, TaskiqDepends(_completion_storer)]


def _payment_service(event: EventDep, dependencies: LifecycleDependenciesDep) -> PaymentService:
    return PaymentService(
        tenant_storage=dependencies.storage_builder.tenants(event.tenant_uid),
    )


PaymentServiceDep = Annotated[PaymentService, TaskiqDepends(_payment_service)]


def _user_storage(event: EventDep, dependencies: LifecycleDependenciesDep) -> UserStorage:
    return dependencies.storage_builder.users(event.tenant_uid)


UserStorageDep = Annotated[UserStorage, TaskiqDepends(_user_storage)]
