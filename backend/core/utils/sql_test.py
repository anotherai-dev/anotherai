# pyright: reportPrivateUsage=false

from typing import Any

import pytest

from core.domain.exceptions import BadRequestError
from core.utils.sql import (
    SQLField,
    SQLGroupBy,
    SQLLimitBy,
    SQLOrderBy,
    SQLQuery,
    SQLSelectField,
    SQLWhereColumn,
    SQLWhereCombined,
    _parse_value,
    sanitize_query,
)


@pytest.mark.parametrize(
    ("input_query", "expected"),
    [
        # Simple select
        pytest.param("select * from users", "SELECT *\nFROM users", id="simple select"),
        # Mixed case and extra spaces
        #         pytest.param(
        #             "  SeLeCt  id, Name  FrOm  Users  ",
        #             """
        # SELECT id,
        #        name
        # FROM users
        # WHERE id = 1
        #   AND name = 'foo'""",
        #             id="mixed case",
        #         ),
        # Operators spacing
        pytest.param("select id+1 as val from users", "SELECT id + 1 AS val\nFROM users", id="operators spacing"),
        # Lowercase identifiers
        # pytest.param("SELECT ID, NAME FROM USERS", "SELECT id, name\nFROM users", id="lowercase identifiers"),
        # Comments are stripped
        pytest.param("SELECT id -- comment\nFROM users", "SELECT id\nFROM users", id="comments are stripped"),
        # Indentation
        # pytest.param(
        #     "select id, name from users where id=1 and name='foo'",
        #     "SELECT id, name FROM users WHERE id = 1 AND name = 'foo'",
        #     id="indentation",
        # ),
    ],
)
def test_sanitize_query_valid(input_query: str, expected: str):
    result = sanitize_query(input_query)
    # Remove trailing spaces and compare
    assert result.strip() == expected.strip()


def test_sanitize_query_multiple_statements():
    with pytest.raises(BadRequestError):
        _ = sanitize_query("select 1; select 2;")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        pytest.param(
            "select * from users",
            SQLQuery(select="*", table="users"),
            id="simple select *",
        ),
        pytest.param(
            "select id from users",
            SQLQuery(select=[SQLSelectField(column="id")], table="users"),
            id="select single column",
        ),
        pytest.param(
            "SELECT * FROM users",
            SQLQuery(select="*", table="users"),
            id="case insensitive keywords upper",
        ),
        pytest.param(
            "SeLeCt * FrOm users",
            SQLQuery(select="*", table="users"),
            id="case insensitive keywords mixed",
        ),
        pytest.param(
            "select id, name from users",
            SQLQuery(select=[SQLSelectField(column="id"), SQLSelectField(column="name")], table="users"),
            id="select multiple columns",
        ),
        pytest.param(
            "select id, name from users where id = 1 and name = 'foo' order by id desc limit 10 offset 5",
            SQLQuery(
                select=[SQLSelectField(column="id"), SQLSelectField(column="name")],
                table="users",
                order_by=[SQLOrderBy(field=SQLField(column="id"), direction="desc")],
                limit=10,
                offset=5,
                where=SQLWhereCombined(
                    operator="AND",
                    columns=[
                        SQLWhereColumn(column=SQLField(column="id"), operator="=", value=1),
                        SQLWhereColumn(column=SQLField(column="name"), operator="=", value="foo"),
                    ],
                ),
            ),
            id="full query",
        ),
        pytest.param(
            "select agent_id, sum(cost_usd), count(*), avg(duration_seconds) from events group by agent_id",
            SQLQuery(
                select=[
                    SQLSelectField(column="agent_id"),
                    SQLSelectField(column="cost_usd", function="sum"),
                    SQLSelectField(column="*", function="count"),
                    SQLSelectField(column="duration_seconds", function="avg"),
                ],
                table="events",
                group_by=SQLGroupBy(fields=[SQLField(column="agent_id")]),
            ),
            id="group by",
        ),
        pytest.param(
            "select * from events limit by 10, 5 user_id",
            SQLQuery(
                select="*",
                table="events",
                limit_by=SQLLimitBy(fields=[SQLField(column="user_id")], limit=10, offset=5),
            ),
            id="limit by",
        ),
        pytest.param(
            "select * from users where jsonExtract(data, '$.name') = 'Alice'",
            SQLQuery(
                select="*",
                table="users",
                where=SQLWhereColumn(
                    column=SQLField(column="data", function="jsonExtract"),
                    operator="=",
                    value="Alice",
                ),
            ),
            id="function in where clause",
        ),
        pytest.param(
            "select * from events where lower(status) = 'completed' and upper(category) = 'SALES'",
            SQLQuery(
                select="*",
                table="events",
                where=SQLWhereCombined(
                    operator="AND",
                    columns=[
                        SQLWhereColumn(
                            column=SQLField(column="status", function="lower"),
                            operator="=",
                            value="completed",
                        ),
                        SQLWhereColumn(
                            column=SQLField(column="category", function="upper"),
                            operator="=",
                            value="SALES",
                        ),
                    ],
                ),
            ),
            id="multiple functions in where clause",
        ),
        pytest.param(
            "select count(*) from users group by substr(email, '@')",
            SQLQuery(
                select=[SQLSelectField(column="*", function="count")],
                table="users",
                group_by=SQLGroupBy(fields=[SQLField(column="email", function="substr")]),
            ),
            id="function in group by clause",
        ),
        pytest.param(
            "select department, count(*) from employees group by upper(department), year(hire_date)",
            SQLQuery(
                select=[
                    SQLSelectField(column="department"),
                    SQLSelectField(column="*", function="count"),
                ],
                table="employees",
                group_by=SQLGroupBy(
                    fields=[
                        SQLField(column="department", function="upper"),
                        SQLField(column="hire_date", function="year"),
                    ],
                ),
            ),
            id="multiple functions in group by clause",
        ),
        # Test integer value parsing
        pytest.param(
            "select * from users where id = 42",
            SQLQuery(
                select="*",
                table="users",
                where=SQLWhereColumn(column=SQLField(column="id"), operator="=", value=42),
            ),
            id="integer value parsing",
        ),
        # Test float value parsing
        pytest.param(
            "select * from products where price = 29.99",
            SQLQuery(
                select="*",
                table="products",
                where=SQLWhereColumn(column=SQLField(column="price"), operator="=", value=29.99),
            ),
            id="float value parsing",
        ),
        # Test string value parsing (single quotes)
        pytest.param(
            "select * from users where name = 'hello'",
            SQLQuery(
                select="*",
                table="users",
                where=SQLWhereColumn(column=SQLField(column="name"), operator="=", value="hello"),
            ),
            id="string value parsing single quotes",
        ),
        # Test string value parsing (double quotes)
        pytest.param(
            'select * from users where name = "world"',
            SQLQuery(
                select="*",
                table="users",
                where=SQLWhereColumn(column=SQLField(column="name"), operator="=", value="world"),
            ),
            id="string value parsing double quotes",
        ),
        # Test negative integer
        pytest.param(
            "select * from accounts where balance = -100",
            SQLQuery(
                select="*",
                table="accounts",
                where=SQLWhereColumn(column=SQLField(column="balance"), operator="=", value=-100),
            ),
            id="negative integer value parsing",
        ),
        # Test negative float
        pytest.param(
            "select * from measurements where temperature = -15.5",
            SQLQuery(
                select="*",
                table="measurements",
                where=SQLWhereColumn(column=SQLField(column="temperature"), operator="=", value=-15.5),
            ),
            id="negative float value parsing",
        ),
        # Test mixed value types in combined where clause
        pytest.param(
            "select * from orders where id = 123 and status = 'pending' and total = 45.67",
            SQLQuery(
                select="*",
                table="orders",
                where=SQLWhereCombined(
                    operator="AND",
                    columns=[
                        SQLWhereColumn(column=SQLField(column="id"), operator="=", value=123),
                        SQLWhereColumn(column=SQLField(column="status"), operator="=", value="pending"),
                        SQLWhereColumn(column=SQLField(column="total"), operator="=", value=45.67),
                    ],
                ),
            ),
            id="mixed value types in combined where",
        ),
        # Function
        pytest.param(
            "select agent_id, COUNT(*), AVG(cost_usd) as avg_cost_usd from users GROUP BY agent_id",
            SQLQuery(
                table="users",
                select=[
                    SQLSelectField(column="agent_id"),
                    SQLSelectField(column="*", function="count"),
                    SQLSelectField(column="cost_usd", function="avg", alias="avg_cost_usd"),
                ],
                group_by=SQLGroupBy(fields=[SQLField(column="agent_id")]),
            ),
            id="function in select",
        ),
        # Additional test cases for alias parsing robustness
        pytest.param(
            "select name as user_name, age AS user_age from users",
            SQLQuery(
                table="users",
                select=[
                    SQLSelectField(column="name", alias="user_name"),
                    SQLSelectField(column="age", alias="user_age"),
                ],
            ),
            id="column aliases with mixed case AS",
        ),
        pytest.param(
            "select MAX(score) AS highest_score, MIN(score) as lowest_score from games",
            SQLQuery(
                table="games",
                select=[
                    SQLSelectField(column="score", function="max", alias="highest_score"),
                    SQLSelectField(column="score", function="min", alias="lowest_score"),
                ],
            ),
            id="function aliases with mixed case AS",
        ),
        pytest.param(
            "select SUM(amount) as total, COUNT(DISTINCT user_id) AS unique_users from transactions",
            SQLQuery(
                table="transactions",
                select=[
                    SQLSelectField(column="amount", function="sum", alias="total"),
                    SQLSelectField(column="DISTINCT user_id", function="count", alias="unique_users"),
                ],
            ),
            id="functions with complex column expressions and aliases",
        ),
        # Test case for agents page query - with CASE and ORDER BY support
        # The SQL parser now supports:
        # - CASE statements in aggregate functions
        # - ORDER BY with column aliases from SELECT clause
        pytest.param(
            "SELECT agent_id, COUNT(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END) as completions_last_7_days, SUM(cost_usd) as total_cost FROM completions GROUP BY agent_id ORDER BY completions_last_7_days DESC, total_cost DESC",
            SQLQuery(
                table="completions",
                select=[
                    SQLSelectField(column="agent_id"),
                    SQLSelectField(
                        column="CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 END",
                        function="count",
                        alias="completions_last_7_days",
                    ),
                    SQLSelectField(column="cost_usd", function="sum", alias="total_cost"),
                ],
                group_by=SQLGroupBy(fields=[SQLField(column="agent_id")]),
                order_by=[
                    SQLOrderBy(field=SQLField(column="completions_last_7_days"), direction="desc"),
                    SQLOrderBy(field=SQLField(column="total_cost"), direction="desc"),
                ],
            ),
            id="agents page query with CASE in COUNT and ORDER BY aliases",
        ),
        # Simpler test case for ORDER BY with aggregate function aliases
        pytest.param(
            "SELECT agent_id, COUNT(*) as total_count FROM completions GROUP BY agent_id ORDER BY total_count DESC",
            SQLQuery(
                table="completions",
                select=[
                    SQLSelectField(column="agent_id"),
                    SQLSelectField(column="*", function="count", alias="total_count"),
                ],
                group_by=SQLGroupBy(fields=[SQLField(column="agent_id")]),
                order_by=[
                    SQLOrderBy(field=SQLField(column="total_count"), direction="desc"),
                ],
            ),
            id="ORDER BY with aggregate alias",
        ),
        # Test case for date functions in WHERE clause - currently failing
        pytest.param(
            "SELECT COUNT(*) as count FROM completions WHERE created_at >= now() - INTERVAL 7 DAY",
            SQLQuery(
                table="completions",
                select=[SQLSelectField(column="*", function="count", alias="count")],
                where=SQLWhereColumn(
                    column=SQLField(column="created_at"),
                    operator=">=",
                    value="now() - INTERVAL 7 DAY",  # This should be parsed as a function/expression, not a string
                ),
            ),
            id="date_function_in_where",
            marks=pytest.mark.xfail(reason="SQL parser doesn't handle function expressions in WHERE clause"),
        ),
    ],
)
def test_sqlquery_from_raw_valid(query: str, expected: SQLQuery):
    result = SQLQuery.from_raw(query)
    assert result == expected


@pytest.mark.parametrize(
    ("query", "match"),
    [
        pytest.param(
            "select * from users; select * from orders",
            "Only one query is supported",
            id="multiple statements",
        ),
        pytest.param(
            "",
            "Only one query is supported",
            id="empty query",
        ),
    ],
)
def test_sqlquery_from_raw_invalid(query: str, match: str):
    with pytest.raises(BadRequestError, match=match):
        _ = SQLQuery.from_raw(query)


@pytest.mark.parametrize(
    ("query", "expected_output"),
    [
        pytest.param(
            SQLQuery(select="*", table="users"),
            "SELECT * FROM users",
            id="simple select *",
        ),
        pytest.param(
            SQLQuery(select=[SQLSelectField(column="id")], table="users"),
            "SELECT id FROM users",
            id="single column",
        ),
        pytest.param(
            SQLQuery(select=[SQLSelectField(column="id"), SQLSelectField(column="name")], table="users"),
            "SELECT id, name FROM users",
            id="multiple columns",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id", alias="user_id")],
                table="users",
            ),
            "SELECT id AS user_id FROM users",
            id="column with alias",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="cost_usd", function="sum")],
                table="events",
            ),
            "SELECT sum(cost_usd) FROM events",
            id="function column",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="cost_usd", function="sum", alias="total_cost")],
                table="events",
            ),
            "SELECT sum(cost_usd) AS total_cost FROM events",
            id="function column with alias",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                where=SQLWhereColumn(column=SQLField(column="id"), operator="=", value=1),
            ),
            "SELECT id FROM users WHERE id = 1",
            id="simple where clause",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                where=SQLWhereCombined(
                    operator="AND",
                    columns=[
                        SQLWhereColumn(column=SQLField(column="id"), operator="=", value=1),
                        SQLWhereColumn(column=SQLField(column="name"), operator="=", value="foo"),
                    ],
                ),
            ),
            "SELECT id FROM users WHERE id = 1 AND name = 'foo'",
            id="combined where clause",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                group_by=SQLGroupBy(fields=[SQLField(column="department")]),
            ),
            "SELECT id FROM users GROUP BY department",
            id="group by single field",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                group_by=SQLGroupBy(fields=[SQLField(column="department"), SQLField(column="role")]),
            ),
            "SELECT id FROM users GROUP BY department, role",
            id="group by multiple fields",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                order_by=[SQLOrderBy(field=SQLField(column="id"), direction="asc")],
            ),
            "SELECT id FROM users ORDER BY id ASC",
            id="order by ascending",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                order_by=[SQLOrderBy(field=SQLField(column="id"), direction="desc")],
            ),
            "SELECT id FROM users ORDER BY id DESC",
            id="order by descending",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                order_by=[
                    SQLOrderBy(field=SQLField(column="name"), direction="asc"),
                    SQLOrderBy(field=SQLField(column="id"), direction="desc"),
                ],
            ),
            "SELECT id FROM users ORDER BY name ASC, id DESC",
            id="order by multiple columns",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                limit=10,
            ),
            "SELECT id FROM users LIMIT 10",
            id="with limit",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                offset=5,
            ),
            "SELECT id FROM users OFFSET 5",
            id="with offset",
        ),
        pytest.param(
            SQLQuery(
                select=[SQLSelectField(column="id")],
                table="users",
                limit=10,
                offset=5,
            ),
            "SELECT id FROM users LIMIT 10 OFFSET 5",
            id="with limit and offset",
        ),
        pytest.param(
            SQLQuery(
                select="*",
                table="events",
                limit_by=SQLLimitBy(fields=[SQLField(column="user_id")], limit=10, offset=5),
            ),
            "SELECT * FROM events LIMIT BY 10, 5 user_id",
            id="limit by clause",
        ),
        pytest.param(
            SQLQuery(
                select=[
                    SQLSelectField(column="agent_id"),
                    SQLSelectField(column="cost_usd", function="sum"),
                    SQLSelectField(column="*", function="count"),
                    SQLSelectField(column="duration_seconds", function="avg", alias="avg_duration"),
                ],
                table="events",
                where=SQLWhereCombined(
                    operator="AND",
                    columns=[
                        SQLWhereColumn(column=SQLField(column="status"), operator="=", value="completed"),
                        SQLWhereColumn(column=SQLField(column="cost_usd"), operator=">", value=0),
                    ],
                ),
                group_by=SQLGroupBy(fields=[SQLField(column="agent_id")]),
                order_by=[SQLOrderBy(field=SQLField(column="agent_id"), direction="asc")],
                limit=100,
            ),
            "SELECT agent_id, sum(cost_usd), count(*), avg(duration_seconds) AS avg_duration FROM events WHERE status = 'completed' AND cost_usd > 0 GROUP BY agent_id ORDER BY agent_id ASC LIMIT 20",
            id="complex query with all clauses",
        ),
    ],
)
def test_sqlquery_format(query: SQLQuery, expected_output: str):
    result = str(query)
    assert result == expected_output


@pytest.mark.parametrize(
    ("query", "expected_output"),
    [
        # Test that integer values are formatted without quotes
        pytest.param(
            SQLQuery(
                select="*",
                table="users",
                where=SQLWhereColumn(column=SQLField(column="id"), operator="=", value=42),
            ),
            "SELECT * FROM users WHERE id = 42",
            id="integer value formatting",
        ),
        # Test that float values are formatted without quotes
        pytest.param(
            SQLQuery(
                select="*",
                table="products",
                where=SQLWhereColumn(column=SQLField(column="price"), operator="=", value=29.99),
            ),
            "SELECT * FROM products WHERE price = 29.99",
            id="float value formatting",
        ),
        # Test that string values are formatted with single quotes
        pytest.param(
            SQLQuery(
                select="*",
                table="users",
                where=SQLWhereColumn(column=SQLField(column="name"), operator="=", value="hello"),
            ),
            "SELECT * FROM users WHERE name = 'hello'",
            id="string value formatting",
        ),
        # Test negative values formatting
        pytest.param(
            SQLQuery(
                select="*",
                table="accounts",
                where=SQLWhereCombined(
                    operator="AND",
                    columns=[
                        SQLWhereColumn(column=SQLField(column="balance"), operator="=", value=-100),
                        SQLWhereColumn(column=SQLField(column="rate"), operator="=", value=-2.5),
                    ],
                ),
            ),
            "SELECT * FROM accounts WHERE balance = -100 AND rate = -2.5",
            id="negative values formatting",
        ),
    ],
)
def test_value_type_formatting(query: SQLQuery, expected_output: str):
    """Test that values are formatted correctly when converting SQLQuery back to string."""
    result = str(query)
    assert result == expected_output


@pytest.mark.parametrize(
    ("input_value", "expected_output", "expected_type"),
    [
        # Integer parsing
        pytest.param("42", 42, int, id="positive integer"),
        pytest.param("-100", -100, int, id="negative integer"),
        pytest.param("0", 0, int, id="zero integer"),
        # Float parsing
        pytest.param("29.99", 29.99, float, id="positive float"),
        pytest.param("-15.5", -15.5, float, id="negative float"),
        pytest.param("0.0", 0.0, float, id="zero float"),
        pytest.param("3.14159", 3.14159, float, id="pi float"),
        # String parsing with single quotes
        pytest.param("'hello'", "hello", str, id="single quoted string"),
        pytest.param("'world with spaces'", "world with spaces", str, id="single quoted string with spaces"),
        pytest.param("''", "", str, id="empty single quoted string"),
        # String parsing with double quotes
        pytest.param('"hello"', "hello", str, id="double quoted string"),
        pytest.param('"world with spaces"', "world with spaces", str, id="double quoted string with spaces"),
        pytest.param('""', "", str, id="empty double quoted string"),
        # Unquoted strings (edge case)
        pytest.param("unquoted", "unquoted", str, id="unquoted string"),
        pytest.param("column_name", "column_name", str, id="column name as string"),
        # Edge cases with whitespace
        pytest.param("  42  ", 42, int, id="integer with whitespace"),
        pytest.param("  'hello'  ", "hello", str, id="quoted string with whitespace"),
    ],
)
def test_parse_value_function(input_value: str, expected_output: Any, expected_type: type):
    """Test the _parse_value function directly to ensure correct type parsing."""
    result = _parse_value(input_value)
    assert result == expected_output
    assert isinstance(result, expected_type)
