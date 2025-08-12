import pytest
import structlog


@pytest.fixture(autouse=True)
def log_capture():
    from structlog.testing import LogCapture

    capture = LogCapture()
    structlog.configure(
        processors=[capture],
    )
    return capture
