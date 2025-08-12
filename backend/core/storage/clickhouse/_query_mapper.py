import json
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import replace
from enum import StrEnum
from typing import Any
from uuid import UUID

from core.domain.exceptions import BadRequestError
from core.storage.clickhouse._models._ch_completion import from_sanitized_metadata
from core.utils.dicts import TwoWayDict
from core.utils.sql import (
    SQLField,
    SQLGroupBy,
    SQLLimitBy,
    SQLOrderBy,
    SQLQuery,
    SQLSelect,
    SQLSelectField,
    SQLWhereColumn,
    SQLWhereCombined,
)
from core.utils.uuid import uuid7_generation_time

_metadata_regexp = r"metadata\.(.*)"
_input_regexp = r"input\.([variables|id|messages].*)"
_output_regexp = r"output\.([error|id|messages].*)"


_ALL_FIELDS = [
    "id",
    "agent_id",
    "input",
    "output",
    "version",
    "duration_seconds",
    "cost_usd",
    "metadata",
    "created_at",
]


class JSONType(StrEnum):
    """An enum for the JSON types supported by clickhouse"""

    FLOAT = "Float"
    INT = "Int"
    STRING = "String"
    BOOLEAN = "Boolean"
    RAW = "Raw"


def _map_json_key(column: str, field: str, type: JSONType):
    splits = field.split(".")
    kp = [int(s) if s.isdigit() else s for s in splits]
    fn = f"simpleJSONExtract{type}" if len(kp) == 1 else f"JSONExtract{type}"
    kp_str = ", ".join(f"'{k}'" if isinstance(k, str) else str(k) for k in kp)
    return f"{fn}({column}, {kp_str})"


def _raw_json_mapper(value: str):
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


_FIELD_MAP = {
    "cost_usd": "cost_millionth_usd / 1000000",
    "duration_seconds": "duration_ds / 10",
    "input.id": "input_id",
    "input.preview": "input_preview",
    "output.id": "output_id",
    "output.preview": "output_preview",
    "version.id": "version_id",
    "version.model": "version_model",
    "metadata": "metadata",
}


def map_query(
    query: str,
    tenant_uid: int,
    agent_uids: TwoWayDict[str, int],
) -> tuple[SQLQuery, Mapping[int, Callable[[Any], Any]]]:
    parsed_query: SQLQuery = SQLQuery.from_raw(query)
    if not parsed_query.table == "completions":
        raise BadRequestError("Only completions table is supported")
    value_mappers: dict[int, Callable[[Any], Any]] = {}
    aliases: dict[str, str] = {}

    def _agent_id_mapper(x: int) -> str:
        try:
            return agent_uids.backward(x)
        except KeyError:
            raise BadRequestError(f"Invalid agent_id: {x}") from None

    select = list(_map_select(parsed_query.select, value_mappers, _agent_id_mapper, aliases))
    group_by = _map_group_by(parsed_query.group_by, aliases) if parsed_query.group_by else None

    # Check if query has aggregate functions
    # TODO: this is a bit brutal since some functions could not be aggregates (ex: json extracts, or toDate)
    # However, ok for now. No matter what we will remove the order by in the future
    # See https://github.com/WorkflowAI/playground/pull/90
    has_aggregates = False
    if parsed_query.select != "*" and isinstance(parsed_query.select, list):
        for col in parsed_query.select:
            if col.function:
                has_aggregates = True
                break

    return SQLQuery(
        select=select,
        table=parsed_query.table,
        where=_map_where_with_tenant(parsed_query.where, tenant_uid, aliases, agent_uids.forward_map),
        group_by=group_by,
        order_by=_map_order_by(parsed_query.order_by, aliases, group_by is not None, has_aggregates),
        limit=parsed_query.limit,
        offset=parsed_query.offset,
        limit_by=_map_limit_by(parsed_query.limit_by, aliases) if parsed_query.limit_by else None,
    ), value_mappers


def _map_where_value(column: str, value: Any, agent_uids: Mapping[str, int]):
    match column:
        case "uuid":
            if not isinstance(value, str):
                raise BadRequestError("id must be a string")
            return UUID(value).int
        case "agent_uid":
            if not isinstance(value, str):
                raise BadRequestError("agent_id must be a string")
            return agent_uids[value]
        case c if c.startswith("metadata["):
            return json.dumps(value)
        case _:
            return value


def _map_where(where: SQLWhereColumn | SQLWhereCombined, aliases: Mapping[str, str], agent_uids: Mapping[str, int]):
    if isinstance(where, SQLWhereColumn):
        field = _map_field(where.column, aliases)
        column_name = aliases.get(field.column, field.column)
        return replace(where, column=field, value=_map_where_value(column_name, where.value, agent_uids))
    return replace(where, columns=[_map_where(col, aliases, agent_uids) for col in where.columns])


def _map_where_with_tenant(
    where: SQLWhereColumn | SQLWhereCombined | None,
    tenant_uid: int,
    aliases: Mapping[str, str],
    agent_uids: Mapping[str, int],
):
    tenant_clause = SQLWhereColumn(column=SQLField(column="tenant_uid"), operator="=", value=tenant_uid)
    if not where:
        return tenant_clause
    if isinstance(where, SQLWhereColumn):
        return SQLWhereCombined(
            operator="AND",
            columns=[tenant_clause, _map_where(where, aliases, agent_uids)],
        )

    value = replace(where, columns=[_map_where(col, aliases, agent_uids) for col in where.columns])
    if value.operator == "AND":
        value.columns = [tenant_clause, *value.columns]
        return value
    return SQLWhereCombined(
        operator="AND",
        columns=[tenant_clause, value],
    )


def _map_group_by(group_by: SQLGroupBy, aliases: dict[str, str]):
    return replace(group_by, fields=[_map_field(field, aliases) for field in group_by.fields])


def _map_order_by(order_by: list[SQLOrderBy] | None, aliases: dict[str, str], has_group_by: bool, has_aggregates: bool):
    if not order_by:
        if has_group_by or has_aggregates:
            # Don't add default ORDER BY when there's GROUP BY or aggregate functions
            return None
        return [
            SQLOrderBy(field=SQLField(column="tenant_uid"), direction="DESC"),
            SQLOrderBy(field=SQLField(column="created_at_date"), direction="DESC"),
            SQLOrderBy(field=SQLField(column="uuid"), direction="DESC"),
        ]
    if has_aggregates and not has_group_by:
        # When using aggregate functions without GROUP BY, don't add tenant_uid to ORDER BY
        return order_by
    return [
        SQLOrderBy(field=SQLField(column="tenant_uid"), direction="DESC"),
        *(replace(order, field=_map_field(order.field, aliases)) for order in order_by),
    ]


def _map_limit_by(limit_by: SQLLimitBy, aliases: dict[str, str]):
    return replace(limit_by, fields=[_map_field(field, aliases) for field in limit_by.fields])


def _map_select(  # noqa: C901
    select: SQLSelect,
    value_mappers: dict[int, Callable[[Any], Any]],
    agent_id_mapper: Callable[[int], str],
    aliases: dict[str, str],
) -> Iterator[SQLSelectField]:
    if select == "*":
        select = [SQLSelectField(column=c) for c in _ALL_FIELDS]
    for idx, col in enumerate(select):
        _alias = col.alias or col.column

        match col.column:
            case "metadata":
                final_column = "metadata"
                value_mappers[idx] = from_sanitized_metadata
            case "input":
                final_column = "input"
                value_mappers[idx] = _raw_json_mapper
            case "output":
                final_column = "output"
                value_mappers[idx] = _raw_json_mapper
            case "version":
                final_column = "version"
                value_mappers[idx] = _raw_json_mapper
            case k if k in _FIELD_MAP:
                final_column = _FIELD_MAP[k]
            case "id":
                value_mappers[idx] = lambda x: str(UUID(int=x))
                final_column = "uuid"
            case "created_at":
                value_mappers[idx] = lambda x: uuid7_generation_time(UUID(int=x))
                final_column = "uuid"
            case "agent_id":
                value_mappers[idx] = agent_id_mapper
                final_column = "agent_uid"
            case c if match := re.match(_metadata_regexp, c):
                value_mappers[idx] = _raw_json_mapper
                final_column = f"metadata['{match.group(1)}']"
            case c if match := re.match(_input_regexp, c):
                value_mappers[idx] = _raw_json_mapper
                final_column = _map_json_key("input", match.group(1), JSONType.STRING)
            case c if match := re.match(_output_regexp, c):
                value_mappers[idx] = _raw_json_mapper
                final_column = _map_json_key("output", match.group(1), JSONType.STRING)
            case _:
                # TODO: check unsupported fields ?
                yield col
                continue

        aliases[_alias] = final_column
        yield replace(col, column=final_column, alias=_alias)


def _map_field(col: SQLField, aliases: Mapping[str, str]):
    # TODO: duplicated from map select to avoid having to do 2 matches in map select.
    # Maybe there is a better way to avoid the duplication
    match col.column:
        case k if k in aliases:
            # The field comes from an alias, so we don't need to map it
            return col
        case "id":
            return replace(col, column="uuid")
        case k if k in _FIELD_MAP:
            return replace(col, column=_FIELD_MAP[k])
        case "agent_id":
            return replace(col, column="agent_uid")
        case c if match := re.match(_metadata_regexp, c):
            return replace(col, column=f"metadata['{match.group(1)}']")
        case c if match := re.match(_input_regexp, c):
            return replace(col, column=_map_json_key("input", match.group(1), JSONType.STRING))
        case c if match := re.match(_output_regexp, c):
            return replace(col, column=_map_json_key("output", match.group(1), JSONType.STRING))
        case _:
            # TODO: check unsupported fields ?
            return col
