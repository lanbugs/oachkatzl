"""Periodic workdir cleanup task.

Runs every 15 minutes via Celery Beat.  Scans GIT_WORKDIR for subdirectories
whose name matches a known Task ID (ObjectId format) and removes them when:

  1. The directory is older than 30 minutes (mtime), AND
  2. The associated Task no longer has an active status
     (i.e. status not in {waiting, starting, running}).

This handles the crash/SIGKILL/cleanup-bug cases that the normal finally-block
in run_task cannot cover.
"""
from __future__ import annotations

import os
import shutil
import time

from app.celery_app import celery


_ACTIVE_STATUSES = {"waiting", "starting", "running"}
_MAX_AGE_SECONDS = 30 * 60   # 30 minutes
_SCAN_INTERVAL   = 15 * 60   # 15 minutes (kept here for documentation)


@celery.task(name="cleanup_workdirs", bind=True, max_retries=0)
def cleanup_workdirs(self) -> dict:
    """Delete stale workdirs that belong to finished or unknown tasks."""
    from app.config import settings

    workdir_root = settings.GIT_WORKDIR
    if not os.path.isdir(workdir_root):
        return {"scanned": 0, "removed": 0, "errors": 0}

    now = time.time()
    scanned = removed = errors = 0

    for entry in os.scandir(workdir_root):
        if not entry.is_dir(follow_symlinks=False):
            continue

        scanned += 1
        task_id = entry.name   # workdir name == task_id (ObjectId hex)

        # Age check — skip young directories (task might still be starting)
        try:
            age = now - entry.stat().st_mtime
        except OSError:
            continue

        if age < _MAX_AGE_SECONDS:
            continue

        # Status check — keep dirs whose task is still active
        try:
            from app.models.task import Task
            task = Task.objects(id=task_id).only("status").first()
            if task and task.status in _ACTIVE_STATUSES:
                continue   # task is genuinely still running — leave it alone
        except Exception:
            # Can't determine status (bad ID format, DB error) — safe to remove
            pass

        # Remove
        try:
            shutil.rmtree(entry.path)
            removed += 1
        except Exception as exc:
            errors += 1
            # Don't let one bad dir abort the whole sweep
            import logging
            logging.getLogger(__name__).warning(
                "cleanup_workdirs: failed to remove %s: %s", entry.path, exc
            )

    return {"scanned": scanned, "removed": removed, "errors": errors}
