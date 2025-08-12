from typing import Any

class _TokenType(tuple[Any]):
    def __getattr__(self, name: str) -> _TokenType: ...

Token = _TokenType()

# Special token types
Text: _TokenType
Whitespace: _TokenType
Newline: _TokenType
Error: _TokenType
# Text that doesn't belong to this lexer (e.g. HTML in PHP)
Other: _TokenType

# Common token types for source code
Keyword: _TokenType
Name: _TokenType
Literal: _TokenType
String: _TokenType
Number: _TokenType
Punctuation: _TokenType
Operator: _TokenType
Comparison: _TokenType
Wildcard: _TokenType
Comment: _TokenType
Assignment: _TokenType

# Generic types for non-source code
Generic: _TokenType
Command: _TokenType

# # String and some others are not direct children of Token.
# # alias them:
# Token.Token = Token
# Token.String = String
# Token.Number = Number

# SQL specific tokens
DML: _TokenType
DDL: _TokenType
CTE: _TokenType
