from copy import deepcopy
from typing import Any, cast

from core.utils.hash import hash_object
from core.utils.strings import slugify


def get_openai_json_schema_name(task_name: str, schema: dict[str, Any]) -> str:
    """Return a unique schema name truncated to 60 characters using the task name and schema hash."""
    # We want to limit the length of the schema name to 60 characters as OpenAI has a limit of 64 characters for the schema name
    # We keep a buffer of 4 character.
    max_schema_name_characters_length = 60

    # We don't know for sure what are the inner workings of the feature at OpenAI,
    # but passing a schema_name which is unique to the schema appeared safer, hence the hash.
    hash_str = hash_object(schema)
    snake_case_name = slugify(task_name).replace("-", "_")
    # Reserve 32 chars for hash and 1 for underscore
    max_name_length = max_schema_name_characters_length - len(hash_str) - 1
    if len(snake_case_name) > max_name_length:
        snake_case_name = snake_case_name[:max_name_length]
    return f"{snake_case_name}_{hash_str}"


# see https://platform.openai.com/docs/guides/structured-outputs#some-type-specific-keywords-are-not-yet-supported
# we remap forbidden keys into the description
# Using an array here to preserve the order of the keys
_INLINE_IN_DESCRIPTION_KEYS = [
    "format",
    "examples",
    "default",
    "minimum",
    "maximum",
    "multipleOf",
    "minLength",
    "maxLength",
    "pattern",
    "minItems",
    "maxItems",
]

# we just remove the keys
_UNSUPPORTED_KEYS = {
    "title",
    "patternProperties",
    "unevaluatedProperties",
    "propertyNames",
    "minProperties",
    "maxProperties",
    "unevaluatedItems",
    "contains",
    "minContains",
    "maxContains",
    "uniqueItems",
}


# TODO: this function is used by more than openai and should be moved elsewhere
# The idea is that it makes all fields required and integrates some unsupported keys
def prepare_openai_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Sanitize and prepare a JSON schema for OpenAI outputs by removing unsupported keys and adjusting types."""
    schema = deepcopy(schema)
    defs = schema.get("$defs", {})

    _sanitize_json_schema_inner(schema, in_defs=False, defs=defs)

    # Remove orphan definitions in $defs that are not referenced in the non-$defs part of the schema
    if "$defs" in schema:
        non_defs = {k: schema[k] for k in schema if k != "$defs"}
        top_level_refs = _collect_refs(non_defs)
        schema["$defs"] = {k: v for k, v in schema["$defs"].items() if k in top_level_refs}

    return schema


def _sanitize_json_schema_inner(schema: dict[str, Any], in_defs: bool, defs: dict[str, Any]) -> None:
    """Recursively sanitize a JSON schema. Inline $ref when in defs context, otherwise keep only the $ref key."""
    if _handle_ref(schema, in_defs, defs):
        return

    _process_forbidden_keys(schema)

    if "properties" in schema:
        _process_properties(schema, in_defs, defs)

    _process_schema_children(schema, in_defs, defs)


def _handle_ref(schema: dict[str, Any], in_defs: bool, defs: dict[str, Any]) -> bool:
    """Handle $ref in schema. Returns True if schema was handled as a ref."""
    if "$ref" not in schema:
        return False

    if in_defs and isinstance(schema["$ref"], str) and schema["$ref"].startswith("#/$defs/"):
        ref_key = schema["$ref"].split("/")[-1]
        if ref_key in defs:
            ref_value = deepcopy(defs[ref_key])
            schema.clear()
            schema.update(ref_value)
            _sanitize_json_schema_inner(schema, in_defs=True, defs=defs)
    else:
        ref = schema["$ref"]
        schema.clear()
        schema["$ref"] = ref
    return True


def _process_schema_children(schema: dict[str, Any], in_defs: bool, defs: dict[str, Any]) -> None:
    """Process child elements of the schema including $defs, items, and anyOf."""
    if (child := schema.get("$defs")) and isinstance(child, dict):
        _process_defs(cast(dict[str, dict[str, Any]], child), defs)

    if child := schema.get("items"):
        _process_items(child, in_defs, defs)

    if (child := schema.get("anyOf")) and isinstance(child, list):
        _process_any_of(cast(list[dict[str, Any]], child), in_defs, defs)


def _process_defs(defs_dict: dict[str, dict[str, Any]], defs: dict[str, Any]) -> None:
    """Process $defs section of the schema."""
    for value in defs_dict.values():
        _sanitize_json_schema_inner(value, in_defs=True, defs=defs)


def _process_items(items: dict[str, Any] | list[Any], in_defs: bool, defs: dict[str, Any]) -> None:
    """Process items section of the schema."""
    if isinstance(items, dict):
        _sanitize_json_schema_inner(items, in_defs, defs)
    else:
        for item in items:
            if isinstance(item, dict):
                _sanitize_json_schema_inner(cast(dict[str, Any], item), in_defs, defs)


def _process_any_of(schemas: list[dict[str, Any]], in_defs: bool, defs: dict[str, Any]) -> None:
    """Process anyOf section of the schema."""
    for subschema in schemas:
        _sanitize_json_schema_inner(subschema, in_defs, defs)


def _process_properties(schema: dict[str, Any], in_defs: bool, defs: dict[str, Any]) -> None:
    """Process schema properties by making non-required properties nullable and sanitizing each property."""
    properties = schema["properties"]
    original_required = set(schema.get("required", []))

    for prop_name, prop_schema in properties.items():
        if prop_name not in original_required:
            _make_nullable(prop_schema)
        _sanitize_json_schema_inner(prop_schema, in_defs, defs)

    schema["required"] = list(properties.keys())
    schema["additionalProperties"] = False


def _process_forbidden_keys(schema: dict[str, Any]) -> None:
    """Inject unsupported keys details into the description and remove them from the schema."""
    agg_description: list[str] = []
    if description := schema.get("description"):
        agg_description.append(description)

    for key in _INLINE_IN_DESCRIPTION_KEYS:
        value = schema.pop(key, None)
        if value is None:
            continue
        if isinstance(value, list):
            value = "\n" + "\n".join(str(item) for item in value)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
        agg_description.append(f"{key}: {value}")

    if agg_description:
        schema["description"] = "\n".join(agg_description)

    for key in _UNSUPPORTED_KEYS:
        schema.pop(key, None)


def _make_nullable(schema: dict[str, Any]) -> None:
    """Modify the schema's type to include 'null' if it is not required."""
    original_type = schema.get("type")
    if isinstance(original_type, list):
        if "null" not in original_type:
            schema["type"] = [*original_type, "null"]
    elif isinstance(original_type, str):
        schema["type"] = [original_type, "null"]


def _collect_refs(item: Any) -> set[str]:
    """Recursively collect all $ref keys from a JSON schema, specifically those referencing $defs."""
    refs: set[str] = set()
    if isinstance(item, dict):
        for k, v in cast(dict[str, Any], item).items():
            if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/"):
                refs.add(v.split("/")[-1])
            else:
                refs |= _collect_refs(v)
    elif isinstance(item, list):
        elem_list: list[Any] = cast(list[Any], item)
        for elem in elem_list:
            refs |= _collect_refs(elem)
    return refs
