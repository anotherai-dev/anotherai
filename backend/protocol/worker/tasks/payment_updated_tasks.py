from core.domain.events import PaymentUpdatedEvent
from protocol.worker._dependencies import PaymentServiceDep
from protocol.worker.tasks._types import TASK
from protocol.worker.worker import broker


@broker.task(retry_on_error=True)
async def trigger_automatic_payment(event: PaymentUpdatedEvent, payment_service: PaymentServiceDep):
    await payment_service.decrement_credits(0)


TASKS: list[TASK[PaymentUpdatedEvent]] = [trigger_automatic_payment]
