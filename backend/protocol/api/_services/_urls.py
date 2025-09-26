from urllib.parse import quote, quote_plus
from uuid import UUID

from core.consts import ANOTHERAI_APP_URL


def experiments_url(experiment_id: str) -> str:
    return f"{ANOTHERAI_APP_URL}/experiments/{experiment_id}"


def view_url(view_id: str) -> str:
    return f"{ANOTHERAI_APP_URL}/views/{view_id}"


def completion_url(run_id: UUID) -> str:
    return f"{ANOTHERAI_APP_URL}/completions/{run_id}"


def deployment_url(deployment_id: str) -> str:
    return f"{ANOTHERAI_APP_URL}/deployments/{quote(deployment_id)}"


def deploy_url(deployment_id: str, completion_id: str) -> str:
    return f"{ANOTHERAI_APP_URL}/deploy?deployment_id={quote_plus(deployment_id)}&completion_id={quote_plus(completion_id)}"
