from typing import TypeGuard


def use_in_memory_broker(broker_url: str | None) -> TypeGuard[str]:
    return not broker_url or broker_url.startswith("memory://")
