from core.domain.events import StoreCompletionEvent
from protocol.worker._dependencies import CompletionStorerDep, PaymentServiceDep
from protocol.worker.tasks._types import TASK
from protocol.worker.worker import broker


@broker.task(retry_on_error=True)
async def store_completion(event: StoreCompletionEvent, completion_storer: CompletionStorerDep) -> None:
    await completion_storer.store_completion(event.completion)


@broker.task(retry_on_error=False)
async def decrement_credits(event: StoreCompletionEvent, payment_service: PaymentServiceDep) -> None:
    if event.completion.cost_usd:
        await payment_service.decrement_credits(event.completion.cost_usd)


TASKS: list[TASK[StoreCompletionEvent]] = [store_completion, decrement_credits]
