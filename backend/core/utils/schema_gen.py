from typing import Any


def schema_from_data(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return {
            "type": "object",
            "properties": {k: schema_from_data(v) for k, v in data.items()},  # pyright: ignore[reportUnknownVariableType]
        }
    if isinstance(data, list):
        if not data:
            return {"type": "array"}
        return {
            "type": "array",
            "items": schema_from_data(data[0]),  # pyright: ignore[reportUnknownVariableType]
        }
    if isinstance(data, bool):
        return {"type": "boolean"}
    if isinstance(data, str):
        return {"type": "string"}
    if isinstance(data, int):
        return {"type": "integer"}
    if isinstance(data, float):
        return {"type": "number"}

    # Not assuming anything on None types
    return {}
