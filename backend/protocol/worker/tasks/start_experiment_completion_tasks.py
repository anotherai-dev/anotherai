from core.domain.events import StartExperimentCompletionEvent
from protocol.worker._dependencies import PlaygroundServiceDep
from protocol.worker.worker import broker


@broker.task(retry_on_error=True)
async def start_experiment_completion(
    event: StartExperimentCompletionEvent,
    playground_service: PlaygroundServiceDep,
):
    await playground_service.start_experiment_completion(event)
