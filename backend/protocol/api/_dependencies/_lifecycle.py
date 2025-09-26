from typing import Annotated

from fastapi import Depends

from protocol._common.lifecycle import LifecycleDependencies


def lifecycle_dependencies() -> LifecycleDependencies:
    # Ok to ignore here, the app will always be initialized when dependencies are called
    return LifecycleDependencies.shared  # pyright: ignore [reportReturnType]


LifecycleDependenciesDep = Annotated[LifecycleDependencies, Depends(lifecycle_dependencies)]
