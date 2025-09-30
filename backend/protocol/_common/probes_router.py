from fastapi import APIRouter, Response

router = APIRouter(prefix="/probes", include_in_schema=False)


# TODO: implement routes, check connection to storage
@router.head("/health")
async def health_head() -> Response:
    return Response(status_code=200)


@router.get("/health")
@router.get("/readiness")
async def readiness() -> Response:
    return Response(status_code=200)
