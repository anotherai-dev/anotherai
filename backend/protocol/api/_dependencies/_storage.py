from typing import Annotated

from fastapi import Depends

from core.storage.agent_storage import AgentStorage
from core.storage.completion_storage import CompletionStorage
from core.storage.file_storage import FileStorage
from core.storage.view_storage import ViewStorage
from protocol.api._dependencies._lifecycle import LifecycleDependenciesDep
from protocol.api._dependencies._tenant import TenantDep


def completion_storage(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> CompletionStorage:
    return dependencies.storage_builder.completions(tenant.uid)


CompletionStorageDep = Annotated[CompletionStorage, Depends(completion_storage)]


def agents_storage(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> AgentStorage:
    return dependencies.storage_builder.agents(tenant.uid)


AgentStorageDep = Annotated[AgentStorage, Depends(agents_storage)]


def file_storage(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> FileStorage:
    return dependencies.storage_builder.files(tenant.uid)


FileStorageDep = Annotated[FileStorage, Depends(file_storage)]


def view_storage(tenant: TenantDep, dependencies: LifecycleDependenciesDep) -> ViewStorage:
    return dependencies.storage_builder.views(tenant.uid)


ViewStorageDep = Annotated[ViewStorage, Depends(view_storage)]
