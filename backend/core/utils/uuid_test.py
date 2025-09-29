from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid1, uuid3, uuid4, uuid5

import pytest
from freezegun import freeze_time

from .uuid import UUID7_REGEXP, is_uuid7, is_zero, uuid7, uuid7_generation_time, uuid_zero


class TestUUID7:
    @freeze_time("2024-01-01")
    def test_uuid7_generation_time(self):
        uuid = uuid7()
        assert uuid7_generation_time(uuid) == datetime(2024, 1, 1, tzinfo=UTC)

    def test_0(self):
        uuid = uuid7(lambda: 0, lambda: 0)
        assert str(uuid) == "00000000-0000-7000-0000-000000000000"

    def test_1(self):
        uuid = uuid7(lambda: 1, lambda: 1)
        assert str(uuid) == "00000000-0001-7000-0000-000000000001"

    def test_consistent_uuid7_from_uuid(self):
        # a uuid4
        uuid = UUID("64fadbdf-1f3c-4f6c-967e-4bc37ab00ec9")
        created_at = datetime(2024, 1, 1, 1, 1, 1, 1, tzinfo=UTC)
        assert uuid.version == 4, "sanity check"

        assert (
            str(uuid7(lambda: int(created_at.timestamp() * 1000), lambda: uuid.int))
            == "018cc289-d0c8-736c-967e-4bc37ab00ec9"
        )


class TestIsUUID7:
    def test_sanity(self):
        uuid = uuid7()
        assert is_uuid7(uuid)

    @pytest.mark.parametrize("gen", [uuid4, lambda: uuid5(uuid4(), "b"), uuid1, lambda: uuid3(uuid4(), "b")])
    def test_is_not_uuid7(self, gen: Callable[[], UUID]):
        assert not is_uuid7(gen())


class TestUUIDRegExp:
    def test_sanity(self):
        assert UUID7_REGEXP.match("00000000-0000-7000-0000-000000000000")


class TestUUIDZero:
    def test_uuid_zero(self):
        assert str(uuid_zero()) == "00000000-0000-0000-0000-000000000000"

    def test_is_zero(self):
        assert is_zero(uuid_zero())
