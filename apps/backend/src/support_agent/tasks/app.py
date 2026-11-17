from celery import Celery

from support_agent.core.config import get_settings

settings = get_settings()
app = Celery(
    "support", broker=settings.redis_url.get_secret_value(), include=["support_agent.tasks.jobs"]
)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_ignore_result=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 120},
    beat_schedule={"outbox": {"task": "support.dispatch", "schedule": 2.0}},
    timezone="UTC",
)
