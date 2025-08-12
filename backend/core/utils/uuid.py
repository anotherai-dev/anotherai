import time
from collections.abc import Callable
from datetime import UTC, datetime
from secrets import randbits
from uuid import UUID


def uuid7(
    ms: Callable[[], int] = lambda: int(time.time() * 1000),
    rand: Callable[[], int] = lambda: randbits(74),
) -> UUID:
    """Generate a UUID7 - a time-ordered UUID

    This implementation focuses on simplicity and readability, not necessarily performance.
    It is also not 100% clear if it respects the RFC spec.
    The timestamp precision is only set to milliseconds. The function also allows hardcoding the
    random bits to get some predictability when needed.

    UUID7 format:
    - 48 bits: Unix timestamp in milliseconds
    - 74 bits: Random or pseudo-random data
    - 6 bits: Version and variant bits
    It is also possible to generate a uuid7 from a another uuid in a consistent manner
    by providing a random_gen that deterministically generates the same number from the same input.
    e-g generate_uuid7(created_at, lambda: uuid.int)
    Returns:
        UUID: A new UUID7 instance
    """

    # Shift timestamp left by 80 bits (leaving space for 74 random bits + 6 version bits)
    # Timestamp is 48 bits
    timestamp_hex = ms() << 80

    # Version is 4 bits starting right after the timestamp
    ver = 7 << 76

    random_bits = rand() & ((1 << 74) - 1)

    # Combine all parts
    uuid_int = timestamp_hex | random_bits | ver

    return UUID(int=uuid_int)


def is_uuid7(uuid: UUID) -> bool:
    """Check if the uuid is a uuid7"""
    # Check if version bits (bits 48-51) are set to 7
    return (uuid.int >> 76) & 0xF == 0x7


def uuid7_generation_time(uuid: UUID) -> datetime:
    """Get the generation time of the uuid"""
    return datetime.fromtimestamp((uuid.int >> 80) / 1000, tz=UTC)
