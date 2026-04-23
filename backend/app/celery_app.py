from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "queue_manager",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.task_handlers.jobs"],
)

celery_app.conf.update(
    accept_content=["json"],
    result_serializer="json",
    task_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    timezone="UTC",
    worker_prefetch_multiplier=1,
)
