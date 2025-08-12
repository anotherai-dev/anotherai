from fastapi import APIRouter

router = APIRouter(prefix="/probes", include_in_schema=False)
