from __future__ import annotations

import io
import json

from apiflask import APIBlueprint, HTTPError
from flask import request, send_file

bp = APIBlueprint("artifacts", __name__)


# ── Auth helpers ─────────────────────────────────────────────────────────────

def _require_artifact_token():
    """Resolve an ArtifactRun from the X-Artifact-Token header. Raises 401 on failure."""
    from app.services.artifact_service import resolve_token
    raw = request.headers.get("X-Artifact-Token", "")
    if not raw:
        raise HTTPError(401, "X-Artifact-Token header required")
    run = resolve_token(raw)
    if run is None:
        raise HTTPError(401, "Invalid or expired artifact token")
    return run


def _load_jwt_user():
    """Load the authenticated user from Bearer token. Returns None if not authenticated."""
    from app.services.rbac import _extract_token, _load_user_from_token
    token = _extract_token()
    if not token:
        return None
    user, _ = _load_user_from_token(token)
    return user


def _check_user_project_access(user, project):
    """Raise 403 if user is not admin and not a member of project."""
    if user.is_admin:
        return
    from app.models.project import ProjectMember
    if not ProjectMember.objects(project=project, user=user).first():
        raise HTTPError(403, "Access denied")


def _check_user_manager_access(user, project):
    """Raise 403 if user doesn't have manager+ role in project."""
    if user.is_admin:
        return
    from app.models.project import ProjectMember
    from app.services.rbac import ROLE_RANKS
    member = ProjectMember.objects(project=project, user=user).first()
    if not member or ROLE_RANKS.get(member.role, 0) < ROLE_RANKS.get("manager", 0):
        raise HTTPError(403, "Manager role required")


def _is_tabular(json_data: str) -> bool:
    """True when json_data is a non-empty list where every element is a dict."""
    try:
        parsed = json.loads(json_data or "")
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


# ── Token-auth endpoints (no JWT required) ──────────────────────────────────

@bp.post("/api/artifacts/upload")
def upload_artifact():
    """Upload a file (multipart) or JSON artifact using an artifact token."""
    from app.services.artifact_service import store_file, store_json

    run = _require_artifact_token()
    ct = request.content_type or ""

    if ct.startswith("multipart/form-data"):
        f = request.files.get("file")
        if not f:
            raise HTTPError(400, "No file in multipart upload (field name: 'file')")
        name = request.form.get("name") or f.filename or "upload"
        data = f.stream.read()
        art = store_file(run, name, io.BytesIO(data), f.content_type or "application/octet-stream", len(data))

    elif ct.startswith("application/json"):
        body = request.get_json(silent=True)
        if not body:
            raise HTTPError(400, "Empty or invalid JSON body")
        name = body.get("name")
        if not name:
            raise HTTPError(400, "Field 'name' is required")
        data_field = body.get("data")
        if data_field is None:
            raise HTTPError(400, "Field 'data' is required")
        art = store_json(run, name, data_field)

    else:
        raise HTTPError(415, "Content-Type must be multipart/form-data or application/json")

    return _artifact_out(art), 201


@bp.get("/api/artifacts/list")
def list_own_artifacts():
    """List all artifacts in the caller's ArtifactRun (token-auth)."""
    from app.models.artifact import Artifact

    run = _require_artifact_token()
    artifacts = Artifact.objects(run=run).order_by("-created_at")
    return [_artifact_out(a) for a in artifacts], 200


@bp.get("/api/artifacts/<artifact_id>/download")
def download_artifact(artifact_id: str):
    """Download an artifact.

    Accepts:
      - X-Artifact-Token header (token of the run owning this artifact)
      - Bearer JWT (user must be a project member)

    Query params:
      ?format=csv   — for JSON artifacts: convert to CSV
    """
    from app.models.artifact import Artifact
    from app.services.artifact_service import json_to_csv

    try:
        art = Artifact.objects.get(id=artifact_id)
    except Artifact.DoesNotExist:
        raise HTTPError(404, "Artifact not found")

    raw_token = request.headers.get("X-Artifact-Token", "")
    if raw_token:
        from app.services.artifact_service import resolve_token
        run = resolve_token(raw_token)
        if run is None or str(run.id) != str(art.run.id):
            raise HTTPError(403, "Token does not grant access to this artifact")
    else:
        user = _load_jwt_user()
        if not user:
            raise HTTPError(401, "Authentication required (X-Artifact-Token or Bearer JWT)")
        try:
            project = art.run.cache.project
        except Exception:
            raise HTTPError(403, "Access denied")
        _check_user_project_access(user, project)

    fmt = request.args.get("format", "")

    if art.artifact_type == "json":
        if fmt == "csv":
            csv_str = json_to_csv(art.json_data or "")
            buf = io.BytesIO(csv_str.encode("utf-8"))
            filename = art.name if art.name.endswith(".csv") else art.name + ".csv"
            return send_file(buf, mimetype="text/csv", as_attachment=True, download_name=filename)
        buf = io.BytesIO((art.json_data or "").encode("utf-8"))
        filename = art.name if art.name.endswith(".json") else art.name + ".json"
        return send_file(buf, mimetype="application/json", as_attachment=True, download_name=filename)

    if art.artifact_type == "file":
        if not art.file_data:
            raise HTTPError(404, "File data not found")
        buf = io.BytesIO(art.file_data.read())
        return send_file(
            buf,
            mimetype=art.content_type or "application/octet-stream",
            as_attachment=True,
            download_name=art.name,
        )

    raise HTTPError(500, "Unknown artifact type")


# ── JWT-auth endpoints (UI access) ──────────────────────────────────────────

@bp.get("/api/artifacts/<artifact_id>")
def get_artifact_meta(artifact_id: str):
    """Fetch artifact metadata. Requires JWT + project membership."""
    from app.models.artifact import Artifact

    user = _load_jwt_user()
    if not user:
        raise HTTPError(401, "Authentication required")

    try:
        art = Artifact.objects.get(id=artifact_id)
    except Artifact.DoesNotExist:
        raise HTTPError(404, "Artifact not found")

    try:
        project = art.run.cache.project
    except Exception:
        raise HTTPError(403, "Access denied")

    _check_user_project_access(user, project)
    return _artifact_out(art), 200


@bp.delete("/api/artifacts/<artifact_id>")
def delete_artifact(artifact_id: str):
    """Delete an artifact. Requires JWT + manager role in the cache's project."""
    from app.models.artifact import Artifact

    user = _load_jwt_user()
    if not user:
        raise HTTPError(401, "Authentication required")

    try:
        art = Artifact.objects.get(id=artifact_id)
    except Artifact.DoesNotExist:
        raise HTTPError(404, "Artifact not found")

    try:
        project = art.run.cache.project
    except Exception:
        raise HTTPError(403, "Access denied")

    _check_user_manager_access(user, project)

    if art.artifact_type == "file":
        try:
            art.file_data.delete()
        except Exception:
            pass
    art.delete()
    return {"message": "Deleted"}, 200
