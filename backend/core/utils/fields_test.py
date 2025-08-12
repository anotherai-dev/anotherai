from core.utils.fields import id_uint32


class TestIDUint32:
    def test_unique(self):
        # Generate multiple IDs to test range and uniqueness
        ids = [id_uint32() for _ in range(10000)]

        # Test range (0 to 2^32 - 1)
        assert all(0 <= id_val < 2**32 for id_val in ids)

        # Test uniqueness (while not guaranteed, highly likely with good random distribution)
        assert len(set(ids)) >= 9999  # Allow for some collisions in rare cases
