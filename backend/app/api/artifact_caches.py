from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from flask import g, request

from app.schemas.artifact import ArtifactCacheIn, ArtifactCacheOut, ArtifactRunOut, ArtifactOut
from app.services.rbac import require_project_role

bp = APIBlueprint("artifact_caches", __name__, url_prefix="/api/projects/<project_id>/artifact-caches")


def _cache_out(c) -> dict:
    return {
        "id":             str(c.id),
        "project_id":     str(c.project.id),
        "name":           c.name,
        "description":    c.description or "",
        "retention_days": c.retention_days or 0,
        "created_at":     c.created_at.isoformat() if c.created_at else None,
    }


def _run_out(run) -> dict:
    from app.models.artifact import Artifact
    count = Artifact.objects(run=run).count()
    cache_name = ""
    try:
        cache_name = run.cache.name
    except Exception:
        pass
    return {
        "id":              str(run.id),
        "cache_id":        str(run.cache.id) if run.cache else None,
        "cache_name":      cache_name,
        "task_id":         str(run.task.id) if run.task else None,
        "workflow_run_id": str(run.workflow_run.id) if run.workflow_run else None,
        "artifact_count":  count,
        "expires_at":      run.expires_at.isoformat() if run.expires_at else None,
        "created_at":      run.created_at.isoformat() if run.created_at else None,
    }


def _is_tabular(json_data: str) -> bool:
    import json as _json
    try:
        parsed = _json.loads(json_data or "")
        return isinstance(parsed, list) and len(parsed) > 0 and all(isinstance(r, dict) for r in parsed)
    except Exception:
        return False


def _artifact_out(a) -> dict:
    return {
        "id":            str(a.id),
        "run_id":        str(a.run.id),
        "name":          a.name,
        "artifact_type": a.artifact_type,
        "content_type":  a.content_type or "application/octet-stream",
        "size_bytes":    a.size_bytes or 0,
        "is_tabular":    _is_tabular(a.json_data) if a.artifact_type == "json" else False,
        "created_at":    a.created_at.isoformat() if a.created_at else None,
    }


# ── Cache CRUD ──────────────────────────────────────────────────────────────

@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
def list_caches(project_id):
    from app.models.artifact import ArtifactCache
    caches = ArtifactCache.objects(project=g.project).order_by("name")
    return [_cache_out(c) for c in caches], 200


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(ArtifactCacheIn, arg_name="body")
def create_cache(project_id, body):
    from app.models.artifact import ArtifactCache
    cache = ArtifactCache(
        project=g.project,
        name=body["name"],
        description=body.get("description", ""),
        retention_days=body.get("retention_days", 30),
    ).save()
    return _cache_out(cache), 201


@bp.patch("/<cache_id>")
@require_project_role("owner", "manager")
@bp.input(ArtifactCacheIn(partial=True), arg_name="body")
def update_cache(project_id, cache_id, body):
    from app.models.artifact import ArtifactCache
    try:
        cache = ArtifactCache.objects.get(id=cache_id, project=g.project)
    except ArtifactCache.DoesNotExist:
        raise HTTPError(404, "Artifact cache not found")
    if "name" in body:
        cache.name = body["name"]
    if "description" in body:
        cache.description = body["description"]
    if "retention_days" in body:
        cache.retention_days = body["retention_days"]
    cache.save()
    return _cache_out(cache), 200


@bp.delete("/<cache_id>")
@require_project_role("owner")
def delete_cache(project_id, cache_id):
    from app.models.artifact import ArtifactCache, ArtifactRun, Artifact
    try:
        cache = ArtifactCache.objects.get(id=cache_id, project=g.project)
    except ArtifactCache.DoesNotExist:
        raise HTTPError(404, "Artifact cache not found")

    for run in ArtifactRun.objects(cache=cache):
        for art in Artifact.objects(run=run):
            if art.artifact_type == "file":
                try:
                    art.file_data.delete()
                except Exception:
                    pass
            art.delete()
        run.delete()

    cache.delete()
    return {"message": "Deleted"}, 200


# ── Runs + Artifacts browse ─────────────────────────────────────────────────

@bp.get("/<cache_id>/runs")
@require_project_role("owner", "manager", "task_runner")
def list_runs(project_id, cache_id):
    from app.models.artifact import ArtifactCache, ArtifactRun
    try:
        cache = ArtifactCache.objects.get(id=cache_id, project=g.project)
    except ArtifactCache.DoesNotExist:
        raise HTTPError(404, "Artifact cache not found")
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (ValueError, TypeError):
        raise HTTPError(400, "Invalid pagination parameters")
    qs    = ArtifactRun.objects(cache=cache).order_by("-created_at")
    total = qs.count()
    items = qs.skip((page - 1) * per_page).limit(per_page)
    return {"items": [_run_out(r) for r in items], "total": total, "page": page, "per_page": per_page}, 200


@bp.get("/<cache_id>/runs/<run_id>/artifacts")
@require_project_role("owner", "manager", "task_runner")
def list_run_artifacts(project_id, cache_id, run_id):
    from app.models.artifact import ArtifactCache, ArtifactRun, Artifact
    try:
        cache = ArtifactCache.objects.get(id=cache_id, project=g.project)
    except ArtifactCache.DoesNotExist:
        raise HTTPError(404, "Artifact cache not found")
    try:
        run = ArtifactRun.objects.get(id=run_id, cache=cache)
    except ArtifactRun.DoesNotExist:
        raise HTTPError(404, "Artifact run not found")
    artifacts = Artifact.objects(run=run).order_by("-created_at")
    return [_artifact_out(a) for a in artifacts], 200
