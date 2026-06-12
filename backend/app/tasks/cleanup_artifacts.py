from __future__ import annotations

import logging

from app.celery_app import celery

log = logging.getLogger(__name__)


def _ensure_mongo() -> None:
    import mongoengine
    from mongoengine.connection import get_connection
    from app.config import settings
    try:
        get_connection().server_info()
    except Exception:
        mongoengine.disconnect_all()
        mongoengine.connect(host=settings.MONGO_URI)


@celery.task(name="cleanup_artifacts")
def cleanup_artifacts() -> None:
    """Delete expired ArtifactRuns and their artifacts (including GridFS files)."""
    _ensure_mongo()
    try:
        from app.services.artifact_service import cleanup_expired
        count = cleanup_expired()
        log.info("cleanup_artifacts: removed %d expired artifact runs", count)
    except Exception as exc:
        log.error("cleanup_artifacts failed: %s", exc, exc_info=True)
