from typing import Literal, NotRequired, TypedDict


class InsertSettings(TypedDict):
    async_insert: NotRequired[Literal[0, 1]]
    wait_for_async_insert: NotRequired[Literal[0, 1]]
