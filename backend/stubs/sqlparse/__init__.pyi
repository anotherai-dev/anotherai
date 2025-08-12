from typing import Literal

from sqlparse import sql

def parse(sql: str, encoding: str | None = None) -> tuple[sql.Statement, ...]: ...
def format(
    sql: str,
    encoding: str | None = None,
    keyword_case: Literal["upper", "lower", "capitalize"] | None = None,
    identifier_case: Literal["upper", "lower", "capitalize"] | None = None,
    strip_comments: bool | None = None,
    use_space_around_operators: bool | None = None,
    reindent: bool | None = None,
    indent_width: int | None = None,
) -> str: ...
