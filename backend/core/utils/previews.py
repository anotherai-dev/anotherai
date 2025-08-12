import logging
from typing import Any

from pydantic import BaseModel


class _MaxLenReachedError(Exception):
    pass


class _Agg:
    def __init__(self, remaining: int):
        self.agg: list[str] = []
        self.remaining = remaining
        self._max_len_reached = False

    def _stringify(self, value: Any) -> str:
        if isinstance(value, float):
            return f"{round(value, 2)}".rstrip("0").rstrip(".")
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value).replace("\n", " ")

    def append(self, val: Any, cut_on_max_len: bool = True):
        s = self._stringify(val)
        if self.remaining < len(s):
            if cut_on_max_len:
                s = s[: self.remaining]
            self.agg.append(s)
            raise _MaxLenReachedError
        self.agg.append(s)
        self.remaining -= len(s)
        if self.remaining == 0:
            raise _MaxLenReachedError

    def __str__(self) -> str:
        raw = "".join(self.agg)
        if self._max_len_reached:
            return raw + "..."
        return raw

    def _append_any(self, value: Any):
        if isinstance(value, dict):
            self._append_dict(value, brackets=True)  # pyright: ignore [reportUnknownArgumentType]
        elif isinstance(value, list):
            self.append("[")
            self._append_list(value)  # pyright: ignore [reportUnknownArgumentType]
            self.append("]")
        elif isinstance(value, str):
            self.append(f'"{value}"')
        else:
            self.append(value)

    @classmethod
    def _file_preview(cls, d: dict[str, Any]):
        content_type = d.get("content_type")
        if not content_type or not isinstance(content_type, str):
            return None

        if (storage_url := d.get("storage_url")) and isinstance(storage_url, str):
            url = storage_url
        elif (url := d.get("url")) and isinstance(url, str):
            pass
        elif (data := d.get("data")) and isinstance(data, str):
            # Not displaying any data here
            url = ""
        else:
            return None

        match content_type.split("/")[0]:
            case "image":
                prefix = "img"
            case "audio":
                prefix = "audio"
            case _:
                prefix = "file"

        return f"[[{prefix}:{url}]]"

    def _append_dict(self, d: dict[str, Any], brackets: bool):
        # For simplification, we consider that any dict
        # with a "content_type" key is a file and should have a specific preview
        if file_preview := self._file_preview(d):
            self.append(file_preview, cut_on_max_len=False)
            return
        if brackets:
            self.append("{")

        for i, (k, v) in enumerate(d.items()):
            if i > 0:
                self.append(", ")
            self.append(k)
            self.append(": ")
            self._append_any(v)

        if brackets:
            self.append("}")

    def _append_list(self, arr: list[Any]):
        for i, v in enumerate(arr):
            if i > 0:
                self.append(", ")
            self._append_any(v)

    def build(self, value: Any):
        try:
            # Not use _any_preview to avoid adding quotes to strings, etc.
            if isinstance(value, dict):
                self._append_dict(value, brackets=False)  # pyright: ignore [reportUnknownArgumentType]
            elif isinstance(value, list):
                self._append_list(value)  # pyright: ignore [reportUnknownArgumentType]
            else:
                self.append(value)
        except _MaxLenReachedError:
            self._max_len_reached = True

        return str(self)


DEFAULT_PREVIEW_MAX_LEN = 255


def compute_preview(model: Any, max_len: int = DEFAULT_PREVIEW_MAX_LEN) -> str:
    """Compute a preview for a given object. All exceptions are handled and a fallback is returned."""
    if not model:
        return "-"

    if isinstance(model, BaseModel):
        model = model.model_dump(exclude_none=True, mode="json")

    try:
        return _Agg(max_len).build(model)
    except Exception:
        logging.getLogger(__name__).exception("error computing preview", extra={"model": model})
        return "..."
