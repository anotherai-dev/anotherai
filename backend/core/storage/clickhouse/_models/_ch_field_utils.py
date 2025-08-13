import json
import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta
from typing import Annotated, Any, cast
from uuid import UUID

from pydantic import AfterValidator, BaseModel, BeforeValidator, PlainSerializer, TypeAdapter

from core.domain.message import Message
from core.utils.uuid import uuid7


def data_and_columns(model: BaseModel, exclude_none: bool = True):
    dumped = model.model_dump(exclude_none=exclude_none)
    data: list[Any] = []
    columns: list[str] = []

    for key, value in dumped.items():
        if isinstance(value, list):
            # Assuming we are in a nested situation
            # if no nested data, skipping adding name and column
            # TODO: this will break for empty arrays of strings that don't have a default
            if not value:
                continue
            # Otherwise we are not in a nested situation
            if isinstance(value[0], dict):
                _handle_nested(key, value, columns, data)  # pyright: ignore[reportUnknownArgumentType]
                continue

        data.append(value)
        columns.append(key)
    return data, columns


def _handle_nested(key: str, value: list[dict[str, Any]], columns: list[str], data: list[Any]):
    # TODO: We assume that all nested items have the same key which is likely
    # not true, we should load the keys from the pydantic annotation instead
    first_dict = value[0]
    subkeys = list(first_dict.keys())
    for subkey in subkeys:
        columns.append(f"{key}.{subkey}")
        data.append([item.get(subkey) for item in value])


def round_to(ndigits: int, /) -> AfterValidator:
    return AfterValidator(lambda v: round(v, ndigits))


RoundedFloat = Annotated[float, round_to(10)]


def parse_ck_str_list[BM: BaseModel](t: type[BM], v: Any) -> list[BM] | None:
    # TODO: this should be extracted into a before validator
    if not v:
        return None
    if not isinstance(v, list):
        raise ValueError("Expected a list")

    return [t.model_validate_json(k) if isinstance(k, str) else t.model_validate(k) for k in v]  # pyright: ignore [reportUnknownVariableType]


def dump_ck_str_list(seq: Sequence[BaseModel]):
    if not seq:
        return list[str]()
    return [t.model_dump_json(by_alias=True, exclude_none=True) for t in seq]


MAX_UINT_8 = 255
MAX_UINT_16 = 65535
MAX_UINT_32 = 4_294_967_295


def validate_int(
    max_value: int,
    log_name: str | None = None,
    warning: bool = True,
    unsigned: bool = True,
) -> AfterValidator:
    def _cap(v: int | None) -> int | None:
        if v is None:
            return None
        if v > max_value:
            if not log_name:
                raise ValueError(f"Value too large {v} > {max_value}")
            if warning:
                logging.getLogger(__name__).warning(
                    f"Value {log_name} too large",  # noqa: G004
                    extra={"value": v, "max_value": max_value},
                )
            return max_value
        if unsigned and v < 0:
            if not log_name:
                raise ValueError(f"Found negative value {v} < 0")
            if warning:
                logging.getLogger(__name__).warning(
                    f"Found negative value {log_name}",  # noqa: G004
                    extra={"value": v},
                )
            return 0
        return v

    return AfterValidator(_cap)


def validate_fixed(size: int = 32, log_name: str | None = None):
    def _validate(v: str) -> str:
        # Clickhouse strings are padded with null bytes, so we need to strip them
        v = v.rstrip("\x00")
        encoded = v.encode("utf-8")
        if len(encoded) > size:
            if not log_name:
                raise ValueError(f"Value must be at most {size} characters long")
            logging.getLogger(__name__).warning(
                f"Value {log_name} too large",  # noqa: G004
                extra={"value": v, "max_value": size},
            )
            # Truncating to the max size, decoding by ignoring errors
            return encoded[:size].decode("utf-8", errors="ignore")
        return v

    return AfterValidator(_validate)


def id_lower_bound(value: datetime):
    # We just 0 the gen as a lower bound
    time_ms = int((value).timestamp() * 1000)
    return uuid7(ms=lambda: time_ms, rand=lambda: 0).int


def id_upper_bound(value: datetime):
    # As an upper bound, we need to add a second to the id
    time_ms = int((value + timedelta(seconds=1)).timestamp() * 1000)
    return uuid7(ms=lambda: time_ms, rand=lambda: 0).int


def serialize_uuid_as_int(uuid: UUID):
    return uuid.int


def parse_uuid_as_int(value: Any):
    if isinstance(value, int):
        return UUID(int=value)
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise ValueError("Invalid run_uuid")


UUID_AS_INT = Annotated[UUID, BeforeValidator(parse_uuid_as_int), PlainSerializer(serialize_uuid_as_int)]


def _map_value(idx: int, value: Any, mapping_fns: Mapping[int, Callable[[Any], Any]]) -> Any:
    mapping_fn = mapping_fns.get(idx)
    return value if mapping_fn is None else mapping_fn(value)


def _map_row(
    row: Sequence[Any],
    column_names: Sequence[str],
    mapping_fns: Mapping[int, Callable[[Any], Any]],
    nested_fields: set[str],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for i, name in enumerate(column_names):
        value = row[i]
        if "." in name and isinstance(value, list) and (splits := name.split(".", 2)) and splits[0] in nested_fields:
            arr = out.setdefault(splits[0], [])
            value = cast(list[Any], value)
            for j, v in enumerate(value):
                try:
                    arr[j][splits[1]] = v
                except IndexError:
                    if j > len(arr):
                        raise IndexError(
                            f"Failed adding nested field {name} to {splits[0]}. "
                            "Index {j} out of range for {len(arr)} len",
                        ) from None
                    arr.append({splits[1]: v})
            continue

        out[name] = _map_value(i, value, mapping_fns)
    return out


def zip_columns(
    column_names: Sequence[str],
    rows: Sequence[Sequence[Any]],
    mapping_fns: Mapping[int, Callable[[Any], Any]] | None = None,
    nested_fields: set[str] | None = None,
) -> list[dict[str, Any]]:
    # For now we just remap the agent_uid to an agent_id
    column_names = list(column_names)
    nested_fields = nested_fields or set()
    mapping_fns = mapping_fns or {}

    return [_map_row(row, column_names, mapping_fns, nested_fields) for row in rows]


# TODO: we should use a duplicated type to avoid side effects
_Messages = TypeAdapter(list[Message])


def dump_messages(messages: list[Message] | None) -> str:
    if not messages:
        return ""
    return _Messages.dump_json(messages, exclude_none=True).decode()


def parse_messages(messages: str) -> list[Message] | None:
    if not messages:
        return None
    return _Messages.validate_json(messages)


def _sanitize_metadata_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _from_sanitized_metadata_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def sanitize_metadata(metadata: dict[str, Any] | None):
    return {k: _sanitize_metadata_value(v) for k, v in metadata.items()} if metadata else {}


def from_sanitized_metadata(metadata: dict[str, str] | None):
    if not metadata:
        return None
    return {k: _from_sanitized_metadata_value(v) for k, v in metadata.items()}


def stringify_json(data: Any) -> str:
    if isinstance(data, BaseModel):
        data = data.model_dump(exclude_none=True)
    # Remove spaces from the JSON string to allow using simplified json queries
    # see https://clickhouse.com/docs/en/sql-reference/functions/json-functions#simplejsonextractstring
    if not data:
        return ""
    return json.dumps(data, separators=(",", ":"))


def from_stringified_json(data: str) -> Any:
    if not data:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return data
