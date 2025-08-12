from typing import Any

from fastapi.responses import JSONResponse

from core.domain.error import Error


def convert_error_response(res: Error, headers: dict[str, Any] | None = None):
    return JSONResponse(
        content={"error": res.model_dump(mode="json", exclude_none=True, by_alias=True)},
        status_code=res.status_code,
        headers=headers,
    )
