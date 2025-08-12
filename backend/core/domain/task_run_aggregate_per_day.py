import datetime
from typing import NamedTuple


class TaskRunAggregatePerDay(NamedTuple):
    date: datetime.date
    total_count: int
    total_cost_usd: float
