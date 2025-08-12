import re
from collections.abc import AsyncIterator
from typing import Any, Protocol

from pydantic import BaseModel
from structlog import get_logger
from structlog.typing import FilteringBoundLogger

_logger = get_logger(__name__)


class _JsonEndError(Exception):
    pass


class _WaitForChunksError(Exception):
    # On look aheads, we have cases where we need to wait for more data
    pass


class JSONStreamError(Exception):
    def __init__(self, message: Any, parser: "JSONStreamParser") -> None:
        super().__init__(message)

        self._dict_stack: list[bool] = parser._dict_stack  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        self.key_path: str = parser.key_path
        self.current_chain: str = parser.current_chain
        self.is_key: bool = parser.is_key
        self.is_value: bool = parser.is_value
        self.is_within_quotes: bool = parser.is_within_quotes
        self.aggregate: list[str] = parser.aggregate
        self.in_json: bool = parser.in_json
        self.is_done: bool = parser.is_done
        self.is_escaping: bool = parser.is_escaping


_ESCAPED_CHARS = {
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}

# all chars that are not valid outside
_outside_of_quotes_chars = set("{]}],-0123456789.nulltruefalse")
# A non whitespace char that is valid after a closing quote
_post_quote_chars = set(",}]\\")


def should_ignore_outside_quotes(c: str) -> bool:
    return c not in _outside_of_quotes_chars


def is_space(c: str) -> bool:
    return c.isspace()


class StreamParser(Protocol):
    @property
    def aggregate(self) -> list[str]: ...

    @property
    def raw_completion(self) -> str: ...

    def process_chunk(self, chunk: str) -> list[tuple[str, Any]] | None: ...


class JSONStreamParser:
    def __init__(self, is_tolerant: bool = True) -> None:
        # To keep track of the key path
        self.path_stack: list[str | int] = []
        # To keep track of the current object or array, true if object
        self._dict_stack: list[bool] = []
        self.key_path: str = ""
        self.current_chain: str = ""  # To keep the current value being read
        self.is_key: bool = False
        self.is_value: bool = False  # To track if we are currently reading a value
        self.is_within_quotes: bool = False  # To track if we are currently reading a string value
        self.aggregate: list[str] = []  # To keep the aggregated data
        self.in_json: bool = False
        self.is_done: bool = False
        self.is_escaping: bool = False
        self._unicode_chars_left: int | None = None
        self._unicode_buffer: str = ""
        self._unicode_escape_type: str = "u"  # Track whether we're processing \u or \x
        self._pending_surrogate: int | None = None
        self.is_tolerant: bool = is_tolerant
        self._leftover_buffer: str = ""
        self._last_char: str = ""

        self.ignore_outside_quotes = should_ignore_outside_quotes if is_tolerant else is_space

    def _exception(self, message: str):
        return JSONStreamError(message, self)

    def _increment_array_idx(self) -> bool:
        if not self.path_stack:
            raise self._exception("Cannot increment array index when not in an array")
        if isinstance(self.path_stack[-1], int):
            self.path_stack[-1] += 1
            self._reset_key_path()
            return True
        return False

    def _reset_key_path(self) -> None:
        self.key_path = ".".join([str(a) for a in self.path_stack])

    def _add_path(self, key: str | int) -> None:
        self.is_value = False
        self.path_stack.append(key)
        self._reset_key_path()

    def _pop_path(self, res: list[tuple[str, Any]] | None) -> None:
        if self.is_value:
            self._finish_current_chain(res)
        try:
            self.path_stack.pop()
        except IndexError as e:
            raise self._exception("Cannot pop path stack when it is empty") from e
        self._reset_key_path()

    def _finish_current_chain(self, res: list[tuple[str, Any]] | None, force: bool = False) -> None:
        """Finish the current chain and append it to the res list if provided"""
        if self.is_key:
            raise self._exception("Cannot finish current chain when in a key")
        if not self.is_value:
            raise self._exception("Cannot finish current chain with no value")
        # current_chain can be empty, for example in "[]"
        if res is not None:
            chain = self._send_current_chain(force)
            if chain:
                res.append(chain)
        self.current_chain = ""
        self.is_value = False

    def _handle_quotes(self, res: list[tuple[str, Any]] | None) -> None:
        """Handles a quote character. Returns true if a value should be streamed"""
        if self.is_within_quotes:
            if self.is_escaping:
                self.is_escaping = False
                self.current_chain += '"'
                return

            if self.is_value:
                next_non_space_char = self._next_non_space_char()
                if next_non_space_char not in _post_quote_chars:
                    # Treat this quote as escaped
                    self._add_to_current_chain('"')
                    return
                # Closing the value, it should be sent
                self._finish_current_chain(res, force=self._last_char == '"')
                self.is_within_quotes = False
                return

            # We are closing the current value
            self.is_within_quotes = False
            # Otherwise we are closing the key
            self._add_path(self.current_chain)
            self.is_key = False
            # Resetting current chain
            self.current_chain = ""
            return

        if self.is_value:
            # We are starting a string value
            self.is_within_quotes = True
            return

        if self.is_key:
            # Raising since is_within_quotes should be True
            raise self._exception("Unexpected quote character in key")

        # Otherwise we are starting a key
        self.is_key = True
        self.is_within_quotes = True
        # TODO: same as below, this is likely what we want in all cases
        # in non tolerant mode we should raise here
        if self.is_tolerant:
            self.current_chain = ""

    def _send_current_chain(self, force: bool = False) -> tuple[str, Any] | None:
        if not self.current_chain and not force:
            return None

        if self.is_within_quotes:
            return (self.key_path, self.current_chain)
        if self.current_chain.startswith("t"):
            return (self.key_path, True)
        if self.current_chain.startswith("f"):
            return (self.key_path, False)
        if self.current_chain.startswith("n"):
            return (self.key_path, None)
        if self.current_chain == "-":
            # Sometimes, we could have the beginning of a negative number
            # In that case we just skip it
            return None
        try:
            return (self.key_path, int(self.current_chain))
        except ValueError:
            try:
                return (self.key_path, float(self.current_chain))
            except ValueError as e:
                raise self._exception(f"Could not parse value '{self.current_chain}'") from e

    def _add_to_current_chain(self, c: str) -> None:
        if self._unicode_chars_left is not None:
            self._unicode_buffer += c
            self._unicode_chars_left -= 1
            if self._unicode_chars_left == 0:
                self._process_unicode_sequence()
            return
        if self.is_escaping:
            if c in _ESCAPED_CHARS:
                self._flush_pending_surrogate()
                self.current_chain += _ESCAPED_CHARS[c]
            elif c in {"u", "x"}:
                self._unicode_chars_left = 4 if c == "u" else 2
                self._unicode_buffer = ""
                self._unicode_escape_type = c
            else:
                self._flush_pending_surrogate()
                self.current_chain += c
            self.is_escaping = False
            return
        if c == "\\":
            self.is_escaping = True
            return
        self._flush_pending_surrogate()
        self.current_chain += c

    def _flush_pending_surrogate(self) -> None:
        if self._pending_surrogate is not None:
            self.current_chain += chr(self._pending_surrogate)
            self._pending_surrogate = None

    def _process_unicode_sequence(self) -> None:
        try:
            code = int(self._unicode_buffer, 16)
        except ValueError:
            # Flush any pending surrogate before handling the error
            self._flush_pending_surrogate()
            # Use the correct escape prefix based on the original escape type
            self.current_chain += f"\\{self._unicode_escape_type}{self._unicode_buffer}"
        else:
            if self._pending_surrogate is not None:
                if 0xDC00 <= code <= 0xDFFF:
                    high = self._pending_surrogate
                    code = ((high - 0xD800) << 10) + (code - 0xDC00) + 0x10000
                    self.current_chain += chr(code)
                    self._pending_surrogate = None
                else:
                    self.current_chain += chr(self._pending_surrogate)
                    self._pending_surrogate = None
                    if 0xD800 <= code <= 0xDBFF:
                        self._pending_surrogate = code
                    else:
                        self.current_chain += chr(code)
            else:
                if 0xD800 <= code <= 0xDBFF:
                    self._pending_surrogate = code
                else:
                    self.current_chain += chr(code)
        self._unicode_chars_left = None
        self._unicode_buffer = ""

    def _next_non_space_char(self) -> str:
        for c in self._leftover_buffer:
            if not is_space(c):
                return c
        raise _WaitForChunksError

    def _process_chunk_inner_loop(self, c: str, res: list[tuple[str, Any]], i: int):  # noqa: C901
        # Returns true if the character was processed, false if the character was ignored
        if c == '"':
            self._handle_quotes(res)
        elif self.is_within_quotes:
            self._add_to_current_chain(c)
        elif c == "{":
            self._dict_stack.append(True)
            # Start of an object, pop the last key
            self.is_value = False
        elif c == "}":
            was_dict = self._dict_stack.pop()
            if not was_dict:
                raise self._exception("Closing a dict when not in a dict")
            # Special handling for empty dicts
            if self._last_char == "{":
                # Checking if we are at the root of the json
                if self.key_path:
                    res.append((self.key_path, {}))
            else:
                # End of an object, pop the last key
                # Not adding res if we are at the first char since it was likely sent
                # before
                self._pop_path(res if i > 0 else None)
            if not self._dict_stack:
                raise _JsonEndError
        elif c == "[":
            self._dict_stack.append(False)
            # Start of an array, push 0 to the path stack
            self._add_path(0)
            # A value could begin immediately after an array
            # e.g. [1,2,3] or ["1"]
            self.is_value = True
        elif c == "]":
            was_dict = self._dict_stack.pop()
            if was_dict:
                raise self._exception("Closing an array when in a dict")
            # Not adding res if we are at the first char since it was likely sent
            # before
            self._pop_path(res if i > 0 else None)
            # Special handling for empty arrays
            if self._last_char == "[":
                res.append((self.key_path, []))
            if not self._dict_stack:
                raise _JsonEndError
        elif c == ":":
            self.is_value = True  # Start reading a value
        elif c == ",":
            # Comma means the value is finished
            # We could still be in a value if the value was not a string
            if self.is_value:
                # Not adding res if we are at the first char since it was likely sent
                # before
                self._finish_current_chain(res if i > 0 else None)
            if not self._increment_array_idx():
                self._pop_path(res)

            if self.current_chain:
                if self.is_tolerant:
                    self.current_chain = ""
                else:
                    raise self._exception("Handling comma with a current chain")
            # A value could begin immediately after a ,
            # e.g. [1,2,3] or ["1","1"]
            if not self._dict_stack[-1]:
                self.is_value = True
        elif not self.ignore_outside_quotes(c):
            # All other characters are ignored

            if not self.is_tolerant and not self.is_value:
                # TODO: this is likely not needed but is left to avoid backwards changes
                # When we are in tolerant mode we want to avoid making changes to is_value
                # for example to handle {\\n"hello": "world"} correctly
                # If we were in a value, se still are e-g True,False
                raise JSONStreamError("Unexpected character outside of quotes", self)
            self.current_chain += c  # Append characters to the current value
        else:
            return False
        return True

    @staticmethod
    def _first_json_index(chunk: str) -> int | None:
        try:
            return chunk.index("{")
        except ValueError:
            try:
                return chunk.index("[")
            except ValueError:
                return None

    @property
    def raw_completion(self) -> str:
        return "".join(self.aggregate)

    def process_chunk(self, chunk: str) -> list[tuple[str, Any]] | None:
        self.aggregate.append(chunk)

        if self.is_done:
            # JSON already parsed, exiting
            return None

        if not self.in_json:
            first_idx = self._first_json_index(chunk)
            if first_idx is None:
                # Still not in json, skipping
                return None
            chunk = chunk[first_idx:]
            self.in_json = True

        res: list[tuple[str, Any]] = []
        i = 0

        self._leftover_buffer += chunk

        while self._leftover_buffer:
            c = self._leftover_buffer[0]
            self._leftover_buffer = self._leftover_buffer[1:]

            try:
                processed = self._process_chunk_inner_loop(c, res=res, i=i)
            except _WaitForChunksError:
                # We need to wait for more data so we break here
                # The current character was not processed, so we add it back to the buffer
                self._leftover_buffer = f"{c}{self._leftover_buffer}"
                return res or None
            except _JsonEndError:
                self.is_done = True
                break

            i += 1
            if processed:
                self._last_char = c

        if self.is_value:
            chain = self._send_current_chain()
            if chain:
                res.append(chain)
        return res or None


def format_model_for_sse(data: BaseModel):
    return f"data: {data.model_dump_json(exclude_none=True)}\n\n"


async def standard_wrap_sse(
    raw: AsyncIterator[bytes],
    termination_chars: bytes = b"\n\n",
    logger: FilteringBoundLogger = _logger,
) -> AsyncIterator[bytes]:
    data = b""
    in_data = False
    async for chunk in raw:
        data += chunk
        if not in_data:
            if data.startswith(b"data: "):
                data = data[6:]
                in_data = True
            else:
                # We will wait for the next chunk, we might be in the middle
                # of 'data: '
                continue

        # Splitting the chunk by separator
        splits = re.split(rb"(?:\r?\n){2}data: ", data)
        if len(splits) > 1:
            # Yielding the rest of the splits except the last one
            for data in splits[0:-1]:
                yield data
            # The last split could be incomplete
            data = splits[-1]

        if data.endswith(termination_chars):
            yield data[: -len(termination_chars)]
            data = b""
            in_data = False

    if data:
        logger.warning("Data left after processing", extra={"data": data})


class RawStreamParser:
    def __init__(self) -> None:
        self.aggregate: list[str] = []

    def process_chunk(self, chunk: str) -> list[tuple[str, Any]]:
        self.aggregate.append(chunk)
        return []

    @property
    def raw_completion(self) -> str:
        return "".join(self.aggregate)
