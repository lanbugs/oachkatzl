from __future__ import annotations

from celery import Celery

from app.config import settings

celery = Celery(
    "oachkatzl",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.run_task",
        "app.tasks.run_workflow",
        "app.tasks.scheduler",
        "app.tasks.cleanup",
        "app.tasks.task_history_cleanup",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        # Poll active schedules every 60 seconds
        "check-schedules": {
            "task": "check_schedules",
            "schedule": 60.0,
        },
        # Remove stale workdirs every 15 minutes
        "cleanup-workdirs": {
            "task": "cleanup_workdirs",
            "schedule": 15 * 60,
        },
        # Delete old task history entries once per hour
        "cleanup-task-history": {
            "task": "cleanup_task_history",
            "schedule": 60 * 60,
        },
    },
)
