import time
from typing import Annotated

from fastapi import Depends, Request


def set_start_time(request: Request) -> float:
    start_time = time.time()
    request.state.start_time = start_time
    return start_time


def _request_start_time(request: Request) -> float:
    return getattr(request.state, "start_time", time.time())


RequestStartDep = Annotated[float, Depends(_request_start_time)]
