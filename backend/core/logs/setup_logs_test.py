# pyright: reportPrivateUsage=false

import json
from datetime import UTC, datetime

from pydantic import BaseModel

from core.logs.setup_logs import _json_serializer


class _TestModel(BaseModel):
    id: int
    name: str | None = None


class TestJSONSerializer:
    def test_base_model(self):
        serialized = _json_serializer(_TestModel(id=1, name="test"))
        assert json.loads(serialized) == {"id": 1, "name": "test"}

    def test_with_datetime(self):
        d = datetime(2021, 1, 1, 0, 0, 0, tzinfo=UTC)
        serialized = _json_serializer({"datetime": d})
        assert json.loads(serialized) == {"datetime": "2021-01-01T00:00:00Z"}
