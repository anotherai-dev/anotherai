from typing import Annotated

from fastapi import Depends, Request

from core.domain.tenant_data import TenantData
from protocol.api._dependencies._lifecycle import LifecycleDependenciesDep


async def authenticated_tenant(request: Request, lifecycle: LifecycleDependenciesDep) -> TenantData:
    authorization = request.headers.get("Authorization", "")
    return await lifecycle.security_service.find_tenant(authorization)


TenantDep = Annotated[TenantData, Depends(authenticated_tenant)]
