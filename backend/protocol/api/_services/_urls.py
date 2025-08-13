from core.consts import ANOTHERAI_APP_URL


def experiments_url(experiment_id: str) -> str:
    return f"{ANOTHERAI_APP_URL}/experiments/{experiment_id}"


def view_url(view_id: str) -> str:
    return f"{ANOTHERAI_APP_URL}/views/{view_id}"


def completion_url(run_id: str) -> str:
    return f"{ANOTHERAI_APP_URL}/completions/{run_id}"
