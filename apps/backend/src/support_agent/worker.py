from support_agent.core.logging import configure_logging
from support_agent.tasks.app import app

configure_logging()

__all__ = ["app"]
