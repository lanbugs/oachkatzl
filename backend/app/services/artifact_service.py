from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import secrets


def _gen_token() -> tuple[str, str]:
    """Return (raw_token, sha256_hex). Only raw is shown once; only hash is stored."""
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_artifact_run(
    cache,
    task=None,
    workflow_run=None,
) -> tuple:
    """Create an ArtifactRun and return (run, raw_token).

    The raw token is returned exactly once and must be passed to the task
    environment. It is never stored in the database — only the SHA-256 hash is.
    """
    from app.models.artifact import ArtifactRun

    raw_token, token_hash = _gen_token()

    expires_at = None
    if cache.retention_days and cache.retention_days > 0:
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=cache.retention_days)

    run = ArtifactRun(
        cache=cache,
        token_hash=token_hash,
        task=task,
        workflow_run=workflow_run,
        expires_at=expires_at,
    )
    run.save()
    return run, raw_token


def resolve_token(raw_token: str):
    """Look up an ArtifactRun by raw token. Returns None if invalid/expired."""
    from app.models.artifact import ArtifactRun

    h = _hash_token(raw_token)
    try:
        run = ArtifactRun.objects.get(token_hash=h)
    except ArtifactRun.DoesNotExist:
        return None

    if run.expires_at and run.expires_at < datetime.datetime.utcnow():
        return None

    return run


def store_json(run, name: str, data: dict | list) -> object:
    """Store a JSON artifact in an ArtifactRun."""
    from app.models.artifact import Artifact

    serialised = json.dumps(data, ensure_ascii=False)
    art = Artifact(
        run=run,
        name=name,
        artifact_type="json",
        content_type="application/json",
        json_data=serialised,
        size_bytes=len(serialised.encode()),
    )
    art.save()
    return art


def store_file(run, name: str, stream, content_type: str, size: int = 0) -> object:
    """Store a file artifact in an ArtifactRun via GridFS."""
    from app.models.artifact import Artifact

    art = Artifact(
        run=run,
        name=name,
        artifact_type="file",
        content_type=content_type or "application/octet-stream",
        size_bytes=size,
    )
    art.save()
    art.file_data.put(stream, content_type=content_type or "application/octet-stream")
    art.size_bytes = art.file_data.length or size
    art.save()
    return art


def json_to_csv(json_str: str) -> str:
    """Convert a JSON string to CSV. Supports list-of-dicts or flat dict."""
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return ""

    buf = io.StringIO()
    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = list(data[0].keys())
        writer = csv.DictWriter(buf, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
    elif isinstance(data, dict):
        writer = csv.writer(buf)
        writer.writerow(list(data.keys()))
        writer.writerow(list(data.values()))
    else:
        buf.write(json_str)

    return buf.getvalue()


def cleanup_expired() -> int:
    """Delete expired ArtifactRuns and their artifacts (including GridFS files).

    Returns the number of runs deleted.
    """
    from app.models.artifact import ArtifactRun, Artifact

    now = datetime.datetime.utcnow()
    expired = ArtifactRun.objects(expires_at__lt=now, expires_at__ne=None)
    count = 0
    for run in expired:
        for art in Artifact.objects(run=run):
            if art.artifact_type == "file":
                try:
                    art.file_data.delete()
                except Exception:
                    pass
            art.delete()
        run.delete()
        count += 1
    return count
