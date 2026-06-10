"""Periodic task-history cleanup.

Runs every hour via Celery Beat.
Reads the global Option ``TASK_HISTORY_DAYS`` (default: 0 = disabled).
Deletes Task documents (+ their TaskLog) older than the configured number of days.
Only finished tasks (success / error / stopped) are removed — active tasks are
never touched regardless of age.
"""
from __future__ import annotations

import datetime
import logging

from app.celery_app import celery

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"success", "error", "stopped"}
_DEFAULT_DAYS      = 0    # 0 = disabled


@celery.task(name="cleanup_task_history", bind=True, max_retries=0)
def cleanup_task_history(self) -> dict:
    from app.models.option import Option
    from app.models.task import Task

    # Read setting
    opt = Option.objects(key="TASK_HISTORY_DAYS").first()
    try:
        days = int(opt.value) if opt else _DEFAULT_DAYS
    except (ValueError, TypeError):
        days = _DEFAULT_DAYS

    if days <= 0:
        return {"status": "disabled", "deleted": 0}

    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    old_tasks = Task.objects(
        created_at__lt=cutoff,
        status__in=list(_TERMINAL_STATUSES),
    )

    deleted = 0
    errors  = 0
    for task in old_tasks:
        try:
            # Remove associated log first
            try:
                from app.models.task_log import TaskLog
                TaskLog.objects(task=task).delete()
            except Exception:
                pass
            task.delete()
            deleted += 1
        except Exception as exc:
            errors += 1
            logger.warning("cleanup_task_history: failed to delete task %s: %s", task.id, exc)

    logger.info(
        "cleanup_task_history: cutoff=%s days=%d deleted=%d errors=%d",
        cutoff.date(), days, deleted, errors,
    )
    return {"status": "ok", "cutoff": cutoff.isoformat(), "deleted": deleted, "errors": errors}
