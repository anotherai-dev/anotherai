import os
from typing import TYPE_CHECKING, Annotated, Any

from pydantic.json_schema import AnyType
from pydantic.json_schema import SkipJsonSchema as PydanticSkipJsonSchema

INCLUDE_PRIVATE_ROUTES = os.getenv("ENV_NAME", "") != "prod"
PRIVATE_TAGS = ["Private"]

PRIVATE_KWARGS: Any = {"include_in_schema": INCLUDE_PRIVATE_ROUTES, "tags": PRIVATE_TAGS}


def _skip_json_schema_annotation(include_private: bool) -> Any:
    if include_private:

        class _IdentityAnnotation:
            def __class_getitem__(cls, item: AnyType) -> AnyType:
                return Annotated[item, cls()]  # pyright: ignore [reportReturnType]

        return _IdentityAnnotation

    return PydanticSkipJsonSchema


if TYPE_CHECKING:
    SkipJsonSchema = Annotated[AnyType, ...]
else:
    SkipJsonSchema = _skip_json_schema_annotation(INCLUDE_PRIVATE_ROUTES)
