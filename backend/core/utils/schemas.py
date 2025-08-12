import contextlib
import re
from collections.abc import Callable, Iterator, Sequence
from typing import (
    Any,
    Literal,
    NotRequired,
    Protocol,
    Self,
    TypedDict,
    cast,
)

FieldType = Literal["string", "number", "integer", "boolean", "object", "array", "null", "array_length", "date"]

# using a single type for json schema for simplicity
# If that is not enough, we could switch to union types or even a pydantic model
RawJsonSchema = TypedDict(
    "RawJsonSchema",
    {
        "$defs": NotRequired[dict[str, "RawJsonSchema"]],
        "title": NotRequired[str],
        "description": NotRequired[str],
        "examples": NotRequired[list[Any]],
        "default": NotRequired[Any],
        "type": FieldType,
        "enum": NotRequired[list[Any]],
        "format": NotRequired[str],
        # Object
        "properties": NotRequired[dict[str, "RawJsonSchema"]],
        "required": NotRequired[list[str]],
        "additionalProperties": NotRequired[bool | dict[str, "RawJsonSchema"]],
        # Array
        "items": NotRequired["RawJsonSchema | list[RawJsonSchema]"],
        # OneOf
        "oneOf": NotRequired[list["RawJsonSchema"]],
        # AnyOf
        "anyOf": NotRequired[list["RawJsonSchema"]],
        # AllOf
        "allOf": NotRequired[list["RawJsonSchema"]],
        # Ref
        "$ref": NotRequired[str],
        "followed_ref_name": NotRequired[str],
    },
    total=False,
)


class InvalidSchemaError(Exception):
    pass


_ONE_OF_KEYS = ("oneOf", "anyOf", "allOf")


class JsonSchema:
    def __init__(
        self,
        schema: RawJsonSchema | dict[str, Any],
        defs: dict[str, "RawJsonSchema"] | None = None,
        is_nullable: bool = False,
        # TODO: it's a bit convoluted but the parent property is only set
        # when the schema is created from a child schema, not when using sub_schema
        parent: tuple["JsonSchema", str | int] | None = None,
    ) -> None:
        self.schema = schema
        self.defs = defs or schema.get("$defs", {})
        self.is_nullable = is_nullable
        self.parent = parent

    @property
    def type(self) -> FieldType | None:
        return self.guess_type(self.schema)

    @property
    def format(self) -> str | None:
        return self.schema.get("format")

    @property
    def title(self) -> str | None:
        return self.schema.get("title")

    @property
    def followed_ref_name(self) -> str | None:
        return self.schema.get("followed_ref_name")

    @classmethod
    def guess_type(cls, schema: RawJsonSchema | dict[str, Any]) -> FieldType | None:
        explicit_type = schema.get("type", None)
        if explicit_type is not None:
            return explicit_type

        if "properties" in schema:
            return "object"
        if "items" in schema:
            return "array"
        return None

    @classmethod
    def _get_def(
        cls,
        uri: str,
        defs: dict[str, "RawJsonSchema"] | None,
        original_schema: RawJsonSchema,
    ) -> RawJsonSchema:
        key = uri.split("/")
        if key[0] != "#":
            raise InvalidSchemaError("Only local refs are supported")
        if len(key) != 3:
            raise InvalidSchemaError(f"Invalid ref {uri}")
        if not defs:
            raise InvalidSchemaError("No definitions found")

        schema = defs.get(key[2])
        if schema is None:
            raise InvalidSchemaError(f"Ref {uri} not found")
        # Not sure why pyright is freaking out here
        # We remove the ref to make sure it is not included in the returned schema and to
        # avoid an infinite recursion
        without_ref = cast(RawJsonSchema, {k: v for k, v in original_schema.items() if k != "$ref"})  # pyright: ignore [reportInvalidCast]
        return {**without_ref, **schema, "followed_ref_name": key[2]}

    @classmethod
    def _one_any_all_of(cls, schema: RawJsonSchema) -> list[RawJsonSchema] | None:
        """Return the components of oneOf, anyOf, allOf if they exist"""
        for key in _ONE_OF_KEYS:
            sub: list[RawJsonSchema] | None = schema.get(key)
            if sub:
                return sub
        return None

    @classmethod
    def splat_nulls(cls, schema: RawJsonSchema) -> tuple[RawJsonSchema, bool]:
        """Returns the sub schema if it contains a oneOf, anyOf, allOf that would represent a nullable value"""
        subs: list[RawJsonSchema] | None = None
        key: Literal["oneOf", "anyOf", "allOf"] | None = None
        for key in _ONE_OF_KEYS:
            subs = schema.get(key)
            if subs:
                break
        if not subs:
            return schema, False

        if len(subs) == 1:
            # This check is duplicated from upstream, but it's ok here
            return subs[0], False

        not_nulls = [sub for sub in subs if sub.get("type") != "null"]
        if len(not_nulls) == 1:
            return not_nulls[0], True
        if len(not_nulls) != len(subs):
            return cast(RawJsonSchema, {key: not_nulls}), True  # pyright: ignore [reportInvalidCast]
        return schema, False

    @classmethod
    def _follow_ref(cls, schema: RawJsonSchema, defs: dict[str, "RawJsonSchema"] | None) -> RawJsonSchema:
        """Returns the sub schema if it contains a $ref"""
        ref = schema.get("$ref")
        if not ref:
            return schema
        return cls._get_def(ref, defs, original_schema=schema)

    @classmethod
    def _supports_key(cls, schema: RawJsonSchema, key: str | int, defs: dict[str, "RawJsonSchema"] | None) -> bool:
        if "$ref" in schema:
            return cls._supports_key(
                cls._get_def(schema["$ref"], defs, original_schema=schema),
                key,
                defs,
            )

        schema_type = cls.guess_type(schema)

        if schema_type == "object":
            return key in schema.get("properties", {})
        if schema_type == "array":
            return key == "items"
        return False

    def __getitem__(self, key: str) -> Any:
        return self.schema[key]  # pyright: ignore [reportUnknownVariableType]

    def __contains__(self, key: str) -> bool:
        return key in self.schema

    @classmethod
    def _raw_child_schema(  # noqa: C901
        cls,
        schema: RawJsonSchema,
        defs: dict[str, "RawJsonSchema"] | None,
        key: str | int,
    ) -> RawJsonSchema:
        schema_type = cls.guess_type(schema)
        if schema_type == "object":
            if "properties" in schema and key in schema["properties"]:
                return schema["properties"][key]
            if (
                "additionalProperties" in schema
                and isinstance(schema["additionalProperties"], dict)
                and key in schema["additionalProperties"]
            ):
                return schema["additionalProperties"][key]
            raise InvalidSchemaError(f"Key {key} not found in object schema")
        if schema_type == "array":
            try:
                idx = int(key)
            except ValueError as e:
                raise InvalidSchemaError(f"Invalid key {key} for array schema") from e
            items = schema.get("items")
            if not items:
                raise InvalidSchemaError("Array schema has no items")
            if isinstance(items, list):
                if idx >= len(items):
                    raise InvalidSchemaError(f"Index {idx} out of range")
                return items[idx]
            return items
        if "$ref" in schema:
            ref = schema.get("$ref")
            if not ref:
                raise InvalidSchemaError("Ref not found")
            return cls._raw_child_schema(cls._get_def(ref, defs, original_schema=schema), defs, key)

        options = cls._one_any_all_of(schema)
        if options:
            for option in options:
                if cls._supports_key(option, key, defs):
                    return cls._raw_child_schema(option, defs, key)
            raise InvalidSchemaError(f"Key {key} not found in oneOf, anyOf, allOf schema")

        raise InvalidSchemaError("Schema is not an object or array")

    def _raw_sub_schema(self, keys: Sequence[str | int]) -> RawJsonSchema:
        schema = cast(RawJsonSchema, self.schema)
        for key in keys:
            schema = self._raw_child_schema(schema, self.defs, key)
        return schema

    def child_schema(
        self,
        key: str | int,
        splat_nulls: bool = True,
        follow_refs: bool = True,
    ) -> Self:
        """Get a direct sub schema based on a key"""
        return self.sub_schema([key], splat_nulls=splat_nulls, follow_refs=follow_refs, parent=(self, key))

    def child_iterator(self, splat_nulls: bool = True, follow_refs: bool = True):
        if self.type == "object":
            # Copying the keys to allow for modifications
            for key in list(self.schema.get("properties", dict[str, Any]()).keys()):
                yield key, self.child_schema(key, splat_nulls, follow_refs)
            return
        if self.type == "array":
            items = self.schema.get("items")
            if not items:
                return
            if isinstance(items, list):
                for idx in range(len(items)):  # pyright: ignore [reportUnknownArgumentType]
                    yield idx, self.child_schema(idx, splat_nulls, follow_refs)
                return
            yield 0, self.child_schema(0, splat_nulls, follow_refs)
            return
        # Nothing to do here, there are no children
        return

    def safe_child_schema(
        self,
        key: str | int,
        splat_nulls: bool = True,
        follow_refs: bool = True,
    ) -> Self | None:
        try:
            return self.child_schema(key, splat_nulls, follow_refs)
        except InvalidSchemaError:
            return None

    def sub_schema(
        self,
        keys: Sequence[str | int] = [],
        keypath: str = "",
        splat_nulls: bool = True,
        follow_refs: bool = True,
        parent: tuple["JsonSchema", str | int] | None = None,
    ) -> Self:
        """
        Get a sub schema based on a list of keys or a keypath

        Args:
            keys (list[str], optional): List of keys to follow. If not provided the keypath is used
            keypath (str, optional): A dot separated keypath. Defaults to "" in which case the self is returned
            splat_nulls (bool, optional): If true, anyOf, allOf, etc. that represent a nullable objects are splat into the schema. Defaults to True.
            follow_refs (bool, optional): If true, the schema will follow the $ref key. Defaults to True.

        Returns:
            JsonSchema: The sub schema
        """
        if not keys:
            if not keypath:
                return self
            keys = keypath.split(".")

        schema = self._raw_sub_schema(keys)
        is_nullable = False

        # Diving into oneOf, anyOf, allOf if only one is there
        one_any_all_of = self._one_any_all_of(schema)
        if one_any_all_of and len(one_any_all_of) == 1:
            schema = one_any_all_of[0]

        if splat_nulls:
            schema, is_nullable = self.splat_nulls(schema)
        if follow_refs:
            schema = self._follow_ref(schema, self.defs)
        return self.__class__(schema, self.defs, is_nullable, parent)

    def get(self, key: str, default: Any = None) -> Any:
        if key in self:
            return self[key]
        return default

    class Navigator(Protocol):
        def __call__(self, schema: "JsonSchema", obj: Any) -> None: ...

    def navigate(self, obj: Any, navigators: Sequence[Navigator]):
        def _dive(key: str | int, value: Any):
            with contextlib.suppress(InvalidSchemaError):
                self.child_schema(key).navigate(value, navigators=navigators)

        if isinstance(obj, dict):
            # Assuming all keys are strings
            for key, value in cast(dict[str, Any], obj).items():
                _dive(key, value)
        elif isinstance(obj, list):
            for idx, value in enumerate(cast(list[Any], obj)):
                _dive(idx, value)

        # TODO: improve by having pre and post navigators?
        # Some navigators like _strip_json_schema_metadata_keys might benefit from running before the dive (to avoid unnecessary recursions)
        for nav in navigators:
            nav(self, obj=obj)

    def fields_iterator(
        self,
        prefix: list[str],
        dive: Callable[[Self], bool] = lambda _: True,
        follow_refs: bool = True,
    ) -> Iterator[tuple[list[str], FieldType, Self]]:
        t = self.type
        if not t:
            return
        if prefix:
            yield prefix, t, self
        if not dive(self):
            return
        match t:
            case "object":
                for key in list(self.schema.get("properties", {}).keys()):
                    yield from self.child_schema(key, follow_refs=follow_refs).fields_iterator(
                        prefix=[*prefix, key],
                        dive=dive,
                    )
            case "array":
                # Assuming array only has one item
                yield from self.child_schema(0, follow_refs=follow_refs).fields_iterator(
                    prefix=[*prefix, "[]"],
                    dive=dive,
                )
            case _:
                pass

    def _remove_property(self, key: str, recursive: bool):
        properties = self.schema.get("properties")
        if not properties:
            return
        properties.pop(key, None)
        if required := self.schema.get("required"):
            required.remove(key)

        if not properties and recursive:
            self.remove_from_parent(recursive=recursive)

    def _remove_item(self, key: int, recursive: bool):
        items = self.schema.get("items")
        if not items:
            return
        if isinstance(items, list):
            _ = items.pop(key)
            if not items and recursive:
                self.remove_from_parent(recursive=recursive)
            return

        _ = self.schema.pop("items")
        if recursive:
            self.remove_from_parent(recursive=recursive)

    def remove_from_parent(self, recursive: bool = True):
        if not self.parent:
            return

        if isinstance(self.parent[1], str):
            self.parent[0]._remove_property(self.parent[1], recursive=recursive)  # noqa: SLF001
            return

        if isinstance(self.parent[1], int):  # pyright: ignore[reportUnnecessaryIsInstance]
            self.parent[0]._remove_item(self.parent[1], recursive=recursive)  # noqa: SLF001
            return


def strip_json_schema_metadata_keys(
    d: Any,
    exc_keys: set[str],
    filter: Callable[[dict[str, Any]], bool] | None = None,
) -> Any:
    _ignore_if_parent = {"properties", "extra_properties", "$defs"}

    def _inner(d: Any, parent: str) -> Any:
        ignore_parent = parent in _ignore_if_parent
        should_strip = True
        if isinstance(d, dict) and filter:
            should_strip = filter(d)  # pyright: ignore[reportUnknownArgumentType]
        if isinstance(d, dict):
            de = cast(dict[str, Any], d)
            include_key = ignore_parent or not should_strip
            return {k: _inner(v, k) for k, v in de.items() if include_key or k not in exc_keys}
        if isinstance(d, list):
            a = cast(list[Any], d)
            return [_inner(v, "") for v in a]
        return d

    return _inner(d, "")


def strip_metadata(d: Any, keys: set[str] | None = None) -> Any:
    _metadata_keys = keys or {
        "title",
        "description",
        "examples",
        "default",
    }
    return strip_json_schema_metadata_keys(d, _metadata_keys)


def add_required_fields(*args: str) -> Callable[[dict[str, Any]], None]:
    def _add_required_fields_to_schema(schema: dict[str, Any]) -> None:
        required = schema.setdefault("required", [])
        required.extend(args)

    return _add_required_fields_to_schema


def make_optional(schema: dict[str, Any]) -> dict[str, Any]:
    return strip_json_schema_metadata_keys(schema, {"required", "minItems", "minLength", "minimum", "enum"})


# Updated regex to exclude line breaks (\n and \r)
_control_char_re = re.compile(r"[\x00-\x09\x0B-\x0C\x0E-\x1F]+")


def clean_json_string(s: str) -> str:
    # Remove control characters except for line breaks
    return _control_char_re.sub("", s)


def remove_extra_keys(schema: JsonSchema, obj: Any):
    if not obj or not isinstance(obj, dict):
        return

    """Use with navigate to remove all extra keys from a schema"""
    if schema.type != "object":
        return
    try:
        properties = set(schema["properties"].keys())
    except KeyError:
        return

    if not properties:
        # When properties is empty, we consider that the object is a freeform object and that extra keys are allowed
        return

    # We do nothing if additionalProperties is truthy
    # The spec of json schema allows complex values for additionalProperties
    # see https://json-schema.org/understanding-json-schema/reference/object#additionalproperties
    # But for now, we only check if it is not False
    if schema.get("additionalProperties"):
        return

    for key in list(cast(dict[Any, Any], obj).keys()):
        if key not in properties:
            del obj[key]


def _handle_missing_required_field(obj: dict[str, Any], key: str, schema: JsonSchema):
    """Adds None if the field is required and not present in the object"""

    child_schema = schema.safe_child_schema(key)
    if not child_schema:
        return

    if child_schema.is_nullable:
        obj[key] = None
        return

    _type = child_schema.get("type")
    if not _type:
        return
    if _type == "null":
        obj[key] = None
        return
    if isinstance(_type, list) and "null" in _type:
        obj[key] = None
        return


def _handle_optional_field(obj: dict[str, Any], key: str, schema: JsonSchema):
    val: Any = obj[key]
    # For now we remove all optional nulls since they should not happen
    if val is None:
        del obj[key]
        return

    # We also remove empty strings but only when they have a format
    # We have seen models return "" for dates for example
    if val == "" and (child_schema := schema.safe_child_schema(key)) and child_schema.get("format"):
        del obj[key]


def sanitize_empty_values(schema: JsonSchema, obj: Any):
    """Use with navigate to:
    - remove all optional nulls and empty strings from a schema.
    Sometimes models return an empty string or null instead of omitting the field
    which can sometimes create schema violations.
    - add missing None when required. the OpenAI proxy sanitizes json schema to make all fields required.
    It also removes all default values.
    So we need to return certain values to pass validation.
    """
    if schema.type != "object":
        return
    if not isinstance(obj, dict):
        return

    properties = schema.schema.get("properties")
    if not properties:
        return

    required = set(schema.get("required", []))
    obj = cast(dict[str, Any], obj)  # ok here since the obj comes from JSON
    for key in properties:
        if key in required:
            if key not in obj:
                _handle_missing_required_field(obj, key, schema)
        else:
            if key in obj:
                _handle_optional_field(obj, key, schema)
