import contextlib
from dataclasses import dataclass
from typing import Any, Literal, override

import sqlparse
from sqlparse.sql import Token, TokenList
from sqlparse.tokens import Keyword, Newline, Whitespace, Wildcard

from core.domain.exceptions import BadRequestError


def sanitize_query(query: str):
    parsed = sqlparse.parse(query)
    if not len(parsed) == 1:
        raise BadRequestError("Only one query is supported")

    return sqlparse.format(
        str(parsed[0]),
        keyword_case="upper",
        identifier_case="lower",
        strip_comments=True,
        use_space_around_operators=True,
        reindent=True,
    )


@dataclass
class SQLField:
    column: str
    function: str | None = None
    # TODO: add function arguments

    @override
    def __str__(self):
        return f"{self.function}({self.column})" if self.function else self.column


@dataclass
class SQLSelectField(SQLField):
    alias: str | None = None

    @override
    def __str__(self):
        base = super().__str__()
        if self.alias and self.alias != self.column:
            return f"{base} AS {self.alias}"
        return base


@dataclass
class SQLGroupBy:
    fields: list[SQLField]

    @override
    def __str__(self):
        return ", ".join(str(field) for field in self.fields)


@dataclass
class SQLWhereColumn:
    """field = value"""

    column: SQLField
    operator: str
    value: Any

    @override
    def __str__(self):
        # Format value properly for SQL output
        formatted_value = f"'{self.value}'" if isinstance(self.value, str) else str(self.value)
        return f"{self.column} {self.operator} {formatted_value}"


@dataclass
class SQLWhereCombined:
    """AND or OR"""

    operator: str
    columns: "list[SQLWhereColumn | SQLWhereCombined]"

    @override
    def __str__(self):
        base = f" {self.operator} ".join(str(col) for col in self.columns)
        if self.operator == "OR":
            return f"({base})"
        return base


@dataclass
class SQLOrderBy:
    field: SQLField
    direction: str


@dataclass
class SQLLimitBy:
    fields: list[SQLField]
    limit: int
    offset: int

    @override
    def __str__(self):
        return f"LIMIT BY {self.limit}, {self.offset}, {', '.join(str(field) for field in self.fields)}"


type SQLSelect = list[SQLSelectField] | Literal["*"]


def _compound_tokens(token: Token) -> list[Token] | None:
    if isinstance(token, TokenList):
        return list(token.tokens)
    return None


@dataclass
class SQLQuery:
    select: SQLSelect
    table: str
    where: SQLWhereColumn | SQLWhereCombined | None = None
    group_by: SQLGroupBy | None = None
    order_by: list[SQLOrderBy] | None = None
    limit: int | None = None
    offset: int | None = None
    limit_by: SQLLimitBy | None = None

    @override
    def __str__(self) -> str:
        """Format the SQL query to a string representation."""
        parts = _format_select_clause(self.select)
        parts.extend(["FROM", self.table])

        if self.where:
            parts.append("WHERE")
            parts.append(str(self.where))

        if self.group_by:
            parts.append("GROUP BY")
            parts.append(str(self.group_by))

        if self.order_by:
            order_parts = [f"{order.field} {order.direction.upper()}" for order in self.order_by]
            parts.extend(["ORDER BY", ", ".join(order_parts)])

        if self.limit_by:
            parts.extend(
                [
                    "LIMIT BY",
                    f"{self.limit_by.limit}, {self.limit_by.offset}",
                    ", ".join(str(field) for field in self.limit_by.fields),
                ],
            )

        if self.limit is not None:
            parts.extend(["LIMIT", str(self.limit)])

        if self.offset is not None:
            parts.extend(["OFFSET", str(self.offset)])

        return " ".join(parts)

    @classmethod
    def from_raw(cls, query: str):  # noqa: C901
        parsed = sqlparse.parse(query)
        if not len(parsed) == 1:
            raise BadRequestError("Only one query is supported")

        statement = parsed[0]

        # Initialize variables
        obj = SQLQuery(select=[], table="")

        # Parse tokens using sqlparse structure
        tokens = list(statement.tokens)

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Skip whitespace tokens
            if token.ttype in (Whitespace, Newline):
                i += 1
                continue

            # Handle SELECT keyword
            if token.ttype is Keyword.DML and token.value.upper() == "SELECT":
                # Find next non-whitespace token
                i += 1
                obj.select, i = _handle_select(tokens, i)
                continue

            # Handle FROM keyword
            if token.ttype is Keyword and token.value.upper() == "FROM":
                # Next non-whitespace token should be the table name
                i += 1
                obj.table, i = _handle_from(tokens, i)
                continue

            # Handle WHERE clause (comes as compound token)
            if token.ttype is None and isinstance(token, TokenList) and str(token.tokens[0]).upper() == "WHERE":
                obj.where = _parse_where_from_compound(token)
                i += 1
                continue

            # Handle ORDER BY keyword (comes as single keyword)
            if token.ttype is Keyword and token.value.upper() == "ORDER BY":
                i += 1
                obj.order_by, i = _handle_order_by(tokens, i)
                continue

            # Handle LIMIT keyword (and LIMIT BY)
            if token.ttype is Keyword and token.value.upper() == "LIMIT":
                # Check if next non-whitespace token is "BY" (for LIMIT BY)
                next_i = i + 1
                while next_i < len(tokens) and tokens[next_i].ttype in (Whitespace, Newline):
                    next_i += 1

                if next_i < len(tokens) and tokens[next_i].ttype is Keyword and tokens[next_i].value.upper() == "BY":
                    # This is LIMIT BY
                    i = next_i + 1  # Skip both LIMIT and BY tokens
                    obj.limit_by, i = _handle_limit_by(tokens, i)
                    continue
                # This is regular LIMIT
                i += 1
                obj.limit, i = _handle_limit(tokens, i)
                continue

            # Handle GROUP BY keyword
            if token.ttype is Keyword and token.value.upper() == "GROUP BY":
                i += 1
                obj.group_by, i = _handle_group_by(tokens, i)
                continue

            # Handle OFFSET keyword
            if token.ttype is Keyword and token.value.upper() == "OFFSET":
                i += 1
                obj.offset, i = _handle_offset(tokens, i)
                continue

            i += 1

        return obj


def _handle_select(tokens: list[Token], start: int) -> tuple[SQLSelect, int]:  # noqa: C901
    i = start
    select_columns: SQLSelect = []
    # Find next non-whitespace token
    while i < len(tokens) and tokens[i].ttype in (Whitespace, Newline):
        i += 1

    if i < len(tokens):
        select_token = tokens[i]
        if select_token.ttype is Wildcard and select_token.value == "*":
            select_columns = "*"
        else:
            # Handle IdentifierList for multiple columns
            if str(select_token.ttype) == "IdentifierList" and (sub_tokens := _compound_tokens(select_token)):
                columns = []
                for subtoken in sub_tokens:
                    if subtoken.ttype is None and hasattr(subtoken, "value"):
                        field_name = subtoken.value.strip()
                        if field_name and field_name != ",":
                            columns.append(_parse_select_column(field_name))
                    elif subtoken.ttype not in (Whitespace, Newline) and str(subtoken.value).strip() not in (",", ""):
                        field_name = str(subtoken.value).strip()
                        if field_name:
                            columns.append(_parse_select_column(field_name))
                select_columns = columns
            else:
                # Single column or comma-separated string
                select_value = select_token.value.strip()
                if "," in select_value:
                    # Handle comma-separated columns as string, respecting parentheses
                    columns = []
                    for col in _split_by_comma_respecting_parens(select_value):
                        if col:
                            columns.append(_parse_select_column(col))
                    select_columns = columns
                elif select_value:
                    select_columns = [_parse_select_column(select_value)]
        i += 1
    return select_columns, i


def _parse_select_column(field_str: str) -> SQLSelectField:
    """Parse a select column string to extract field name, function, and alias."""
    field_str = field_str.strip()

    # Check for alias pattern with " as " or " AS "
    alias = None
    if " as " in field_str.lower():
        # Find the last occurrence of " as " (case insensitive)
        field_lower = field_str.lower()
        as_index = field_lower.rfind(" as ")
        if as_index != -1:
            alias = field_str[as_index + 4 :].strip()
            field_str = field_str[:as_index].strip()

    # Check for function pattern like sum(cost_usd), count(*), avg(duration_seconds)
    if "(" in field_str and field_str.endswith(")"):
        func_name = field_str.split("(")[0].strip().lower()
        field_content = field_str[field_str.find("(") + 1 : -1].strip()
        return SQLSelectField(column=field_content, function=func_name, alias=alias)

    # No function, just return the field name with possible alias
    return SQLSelectField(column=field_str, alias=alias)


def _parse_field_with_function(field_str: str) -> SQLField:
    """Parse a field string to extract field name and function for WHERE/GROUP BY clauses."""
    field_str = field_str.strip()

    # Check for function pattern like jsonExtract(data, '$.name'), lower(status), etc.
    if "(" in field_str and field_str.endswith(")"):
        func_name = field_str.split("(")[0].strip()  # Preserve original case
        # For functions with parameters, we need to extract just the column name (first parameter)
        field_content = field_str[field_str.find("(") + 1 : -1].strip()

        # Handle functions with multiple parameters - take the first one as the column
        column_name = field_content.split(",")[0].strip() if "," in field_content else field_content

        return SQLField(column=column_name, function=func_name)

    # No function, just return the field name
    return SQLField(column=field_str)


def _handle_from(tokens: list[Token], start: int) -> tuple[str, int]:
    i = start
    while i < len(tokens) and tokens[i].ttype in (Whitespace, Newline):
        i += 1

    table_name = ""
    if i < len(tokens):
        table_name = tokens[i].value.strip()
        i += 1
    return table_name, i


def _parse_value(value_str: str) -> int | float | str:
    """Parse a value string to its proper type (int, float, or string without quotes)."""
    value_str = value_str.strip()

    # Try parsing as integer
    try:
        return int(value_str)
    except ValueError:
        pass

    # Try parsing as float
    try:
        return float(value_str)
    except ValueError:
        pass

    # Handle quoted strings - remove surrounding quotes
    if (value_str.startswith("'") and value_str.endswith("'")) or (
        value_str.startswith('"') and value_str.endswith('"')
    ):
        return value_str[1:-1]

    # Return as-is for unquoted strings
    return value_str


def _parse_where_from_compound(compound_token: TokenList) -> SQLWhereColumn | SQLWhereCombined | None:
    """Parse WHERE clause from a compound token."""
    if not compound_token.tokens:
        return None

    tokens = compound_token.tokens
    where_columns: list[SQLWhereColumn | SQLWhereCombined] = []
    current_operator = None

    i = 1  # Skip the "WHERE" keyword
    while i < len(tokens):
        token = tokens[i]

        # Skip whitespace
        if token.ttype in (Whitespace, Newline):
            i += 1
            continue

        # Look for AND/OR operators
        if str(token).upper() in ("AND", "OR"):
            current_operator = str(token).upper()
            i += 1
            continue

        # Parse conditions like "id = 1" or "name = 'foo'" or "jsonExtract(data, '$.name') = 'Alice'"
        condition_str = str(token).strip()
        if "=" in condition_str:
            parts = condition_str.split("=", 1)
            if len(parts) == 2:
                column_str = parts[0].strip()
                value_str = parts[1].strip()

                # Parse column for potential function call
                column_field = _parse_field_with_function(column_str)
                # Parse value to proper type
                parsed_value = _parse_value(value_str)
                where_columns.append(SQLWhereColumn(column=column_field, operator="=", value=parsed_value))

        i += 1

    # Return the appropriate WHERE structure
    if len(where_columns) == 1:
        return where_columns[0]
    if len(where_columns) > 1:
        return SQLWhereCombined(operator=current_operator or "AND", columns=where_columns)
    return None


def _handle_order_by(tokens: list[Token], start: int) -> tuple[list[SQLOrderBy] | None, int]:
    i = start
    while i < len(tokens) and tokens[i].ttype in (Whitespace, Newline):
        i += 1

    # Parse the ORDER BY value which comes as a compound token like "id desc, name asc"
    if i < len(tokens):
        order_token = tokens[i]
        order_by_list = []

        # Get the full ORDER BY string
        order_str = str(order_token).strip()

        # Split by comma to get individual ORDER BY fields
        order_fields = _split_by_comma_respecting_parens(order_str)

        for field_str in order_fields:
            field_str = field_str.strip()  # noqa: PLW2901
            if not field_str:
                continue

            # Parse each field for column and direction
            parts = field_str.split()
            if parts:
                column = parts[0]
                direction = "asc"  # default

                # Check if last part is a direction keyword
                if len(parts) > 1 and parts[-1].upper() in ("ASC", "DESC"):
                    direction = parts[-1].lower()
                    # Reconstruct column name without the direction
                    column = " ".join(parts[:-1])
                else:
                    # No direction specified, use the whole string as column
                    column = field_str

                order_by_list.append(SQLOrderBy(field=_parse_field_with_function(column), direction=direction))

        if order_by_list:
            return order_by_list, i + 1

    return None, i


def _handle_limit(tokens: list[Token], start: int) -> tuple[int | None, int]:
    i = start
    while i < len(tokens) and tokens[i].ttype in (Whitespace, Newline):
        i += 1

    if i < len(tokens):
        try:
            limit_value = int(tokens[i].value.strip())
            return limit_value, i + 1
        except ValueError:
            pass

    return None, i


def _handle_offset(tokens: list[Token], start: int) -> tuple[int | None, int]:
    i = start
    while i < len(tokens) and tokens[i].ttype in (Whitespace, Newline):
        i += 1

    if i < len(tokens):
        try:
            offset_value = int(tokens[i].value.strip())
            return offset_value, i + 1
        except ValueError:
            pass

    return None, i


def _handle_group_by(tokens: list[Token], start: int) -> tuple[SQLGroupBy | None, int]:
    i = start
    while i < len(tokens) and tokens[i].ttype in (Whitespace, Newline):
        i += 1

    if i < len(tokens):
        group_token = tokens[i]
        if isinstance(group_token, TokenList):
            # For TokenList, reconstruct the full field expression
            field_str = str(group_token).strip()
            if field_str:
                # Split by comma to handle multiple fields, but be careful of commas inside functions
                fields: list[str] = _split_group_by_fields(field_str)
                return SQLGroupBy(fields=[_parse_field_with_function(field) for field in fields]), i + 1
        else:
            # Simple case - single field
            field = str(group_token).strip()
            if field:
                return SQLGroupBy(fields=[_parse_field_with_function(field)]), i + 1

    return None, i


def _split_group_by_fields(field_str: str) -> list[str]:
    """Split GROUP BY fields by comma, but handle commas inside function parentheses."""
    return _split_by_comma_respecting_parens(field_str)


def _split_by_comma_respecting_parens(field_str: str) -> list[str]:
    """Split a string by comma, but handle commas inside parentheses (including nested)."""
    fields = []
    current_field = ""
    paren_depth = 0

    for char in field_str:
        if char == "(":
            paren_depth += 1
            current_field += char
        elif char == ")":
            paren_depth -= 1
            current_field += char
        elif char == "," and paren_depth == 0:
            # Only split on comma if we're not inside parentheses
            if current_field.strip():
                fields.append(current_field.strip())
            current_field = ""
        else:
            current_field += char

    # Add the last field
    if current_field.strip():
        fields.append(current_field.strip())

    return fields


def _handle_limit_by(tokens: list[Token], start: int) -> tuple[SQLLimitBy | None, int]:  # noqa: C901
    i = start
    while i < len(tokens) and tokens[i].ttype in (Whitespace, Newline):
        i += 1

    # LIMIT BY syntax: "limit by 10, 5 user_id" means limit=10, offset=5, fields=["user_id"]
    if i < len(tokens):
        limit_by_token = tokens[i]
        if isinstance(limit_by_token, TokenList):
            # Parse sub-tokens from IdentifierList
            # Structure: [Integer '10', Punctuation ',', Whitespace ' ', Identifier '5 user_id']
            limit_val = None
            offset_val = None
            fields: list[str] = []

            for subtoken in limit_by_token.tokens:
                subtoken_str = str(subtoken).strip()
                if subtoken.ttype and str(subtoken.ttype) == "Token.Literal.Number.Integer":
                    # This is the limit value (first integer)
                    if limit_val is None:
                        with contextlib.suppress(ValueError):
                            limit_val = int(subtoken_str)

                elif subtoken.ttype is None and subtoken_str and subtoken_str not in (",", ""):
                    # This is an Identifier containing "5 user_id"
                    parts = subtoken_str.split()
                    if len(parts) >= 2 and offset_val is None:
                        try:
                            offset_val = int(parts[0])
                            fields.extend(parts[1:])
                        except ValueError:
                            # If first part is not a number, treat whole thing as fields
                            fields.extend(parts)
                    else:
                        fields.extend(parts)

            if limit_val is not None and offset_val is not None and fields:
                return SQLLimitBy(
                    fields=[_parse_field_with_function(field) for field in fields],
                    limit=limit_val,
                    offset=offset_val,
                ), i + 1
        else:
            # Simple case - parse string like "10, 5 user_id"
            limit_by_str = str(limit_by_token).strip()
            parts = limit_by_str.replace(",", " ").split()
            if len(parts) >= 3:
                try:
                    limit_val = int(parts[0])
                    offset_val = int(parts[1])
                    fields = parts[2:]
                    return SQLLimitBy(
                        fields=[_parse_field_with_function(field) for field in fields],
                        limit=limit_val,
                        offset=offset_val,
                    ), i + 1
                except ValueError:
                    pass

    return None, i


def _format_select_clause(select: SQLSelect) -> list[str]:
    """Format the SELECT clause."""
    parts = ["SELECT"]
    if select == "*":
        parts.append("*")
        return parts

    parts.append(", ".join(str(col) for col in select))
    return parts
