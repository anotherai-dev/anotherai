from core.domain.events import UserConnectedEvent
from protocol.worker._dependencies import UserStorageDep
from protocol.worker.tasks._types import TASK
from protocol.worker.worker import broker


@broker.task(retry_on_error=True)
async def user_authenticated_task(event: UserConnectedEvent, user_storage: UserStorageDep):
    await user_storage.set_last_used_organization(event.user_id, event.organization_id)


TASKS: list[TASK[UserConnectedEvent]] = [user_authenticated_task]
