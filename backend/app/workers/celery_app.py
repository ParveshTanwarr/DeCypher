"""Celery application configuration for autonomous scanning."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "decypher",
    broker=settings.REDIS_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "dispatch-due-autoscans": {
            "task": "decypher.dispatch_due_scans",
            "schedule": 60.0,
        },
        "dispatch-due-collection": {
            "task": "decypher.dispatch_due_collection",
            "schedule": max(60, settings.COLLECTION_POLL_INTERVAL_MINUTES * 60),
        },
    },
)

import app.workers.tasks  # noqa: E402,F401
