import json
import urllib.request
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


def test_server_json_is_valid():
    """Validate server.json against the MCP registry schema."""
    # Read server.json from project root
    project_root = Path(__file__).parent.parent.parent.parent
    server_json_path = project_root / "server.json"

    assert server_json_path.exists(), "server.json not found in project root"

    with open(server_json_path) as f:
        server_config = json.load(f)

    # Get schema URL
    schema_url = server_config.get("$schema")
    assert schema_url, "No $schema found in server.json"

    # Fetch the schema
    with urllib.request.urlopen(schema_url) as response:  # noqa: S310
        schema = json.loads(response.read())

    # Validate
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(server_config))

    if errors:
        error_messages = []
        for error in errors:
            path = " -> ".join(str(p) for p in error.path)
            error_messages.append(f"{error.message} (at {path})")
        pytest.fail("server.json validation failed:\n" + "\n".join(error_messages))

    # Additional assertions
    assert server_config["name"] == "dev.anotherai/anotherai"
    assert server_config["deployment"]["type"] == "remote"
    assert server_config["deployment"]["remote"]["url"] == "https://api.anotherai.dev/mcp"
