from __future__ import annotations

import datetime
import hashlib
import json
import secrets

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Boolean, String
from apiflask.schemas import Schema
from flask import g, request

from app.services.rbac import require_project_role

bp = APIBlueprint("template_tokens", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────

def _generate_token() -> tuple[str, str]:
    """Return (raw_token, sha256_hex). Only raw is shown once; only hash is stored."""
    raw = secrets.token_urlsafe(32)   # 32 bytes = 256 bits of entropy
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _token_out(tt, raw: str | None = None) -> dict:
    return {
        "id":              str(tt.id),
        "name":            tt.name,
        "survey_defaults": tt.survey_defaults or "{}",
        "created_at":      tt.created_at.isoformat() if tt.created_at else None,
        "expires_at":      tt.expires_at.isoformat() if tt.expires_at else None,
        "active":          tt.active,
        # Only included on creation — never returned again
        **({"token": raw} if raw is not None else {}),
    }


# ── Schemas ───────────────────────────────────────────────────────────────

class TokenCreateIn(Schema):
    name             = String(required=True)
    survey_defaults  = String(load_default="{}")   # JSON: pre-filled survey answers
    expires_at       = String(load_default=None)   # ISO datetime, optional


class ExecuteIn(Schema):
    survey_answers = String(load_default="{}")     # JSON: override token defaults
    build_task_id  = String(load_default=None)     # deploy-type: which build to deploy


# ── CRUD (project-scoped, requires manager+) ──────────────────────────────

@bp.get("/api/projects/<project_id>/templates/<template_id>/tokens")
@require_project_role("owner", "manager")
def list_tokens(project_id, template_id):
    from app.models.template_token import TemplateToken
    from app.models.template import Template
    try:
        tmpl = Template.objects.get(id=template_id, project=g.project)
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")
    tokens = TemplateToken.objects(template=tmpl, active=True)
    return [_token_out(tt) for tt in tokens], 200


@bp.post("/api/projects/<project_id>/templates/<template_id>/tokens")
@require_project_role("owner", "manager")
@bp.input(TokenCreateIn, arg_name="body")
def create_token(project_id, template_id, body):
    from app.models.template_token import TemplateToken
    from app.models.template import Template

    try:
        tmpl = Template.objects.get(id=template_id, project=g.project)
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")

    # Validate survey_defaults JSON
    try:
        json.loads(body.get("survey_defaults", "{}"))
    except (json.JSONDecodeError, TypeError):
        raise HTTPError(400, "survey_defaults must be valid JSON")

    expires_at = None
    if body.get("expires_at"):
        try:
            expires_at = datetime.datetime.fromisoformat(body["expires_at"])
        except ValueError:
            raise HTTPError(400, "Invalid expires_at format (use ISO 8601)")

    raw, hashed = _generate_token()
    tt = TemplateToken(
        template        = tmpl,
        project         = g.project,
        name            = body["name"],
        token_hash      = hashed,
        survey_defaults = body.get("survey_defaults", "{}"),
        expires_at      = expires_at,
    ).save()

    return _token_out(tt, raw=raw), 201


@bp.delete("/api/projects/<project_id>/templates/<template_id>/tokens/<token_id>")
@require_project_role("owner", "manager")
def delete_token(project_id, template_id, token_id):
    from app.models.template_token import TemplateToken
    try:
        tt = TemplateToken.objects.get(id=token_id, project=g.project)
        tt.active = False
        tt.save()
    except TemplateToken.DoesNotExist:
        raise HTTPError(404, "Token not found")
    return {"message": "Token revoked"}, 200


# ── Public execute endpoint (no auth — token IS the credential) ───────────

@bp.post("/api/execute/<raw_token>")
def execute(raw_token: str):
    """Trigger a template run using an execute token.

    Optional JSON body::

        {
          "survey_answers": {"env": "production"},
          "build_task_id": "<task_id>"
        }

    ``survey_answers`` in the request body *override* the token's defaults.
    Any survey variable not supplied falls back to the token default, then to
    the template default.

    For **deploy-type** templates ``build_task_id`` is required and must be the
    ``id`` of a successful build task belonging to the associated build template.
    The token's ``survey_defaults`` may also store a ``_build_task_id`` key as
    a convenience default (overridden by the request body value).
    """
    from app.models.template_token import TemplateToken
    from app.services.task_service import create_task, enqueue_task

    token_hash = _hash_token(raw_token)
    tt = TemplateToken.objects(token_hash=token_hash, active=True).first()

    if not tt:
        raise HTTPError(401, "Invalid or revoked execute token")

    if tt.expires_at and tt.expires_at < datetime.datetime.utcnow():
        raise HTTPError(401, "Execute token has expired")

    template = tt.template

    # Merge survey answers: token defaults ← request body overrides
    defaults: dict = {}
    try:
        defaults = json.loads(tt.survey_defaults or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    body = request.get_json(silent=True) or {}
    try:
        overrides = json.loads(body.get("survey_answers") or "{}") \
            if isinstance(body.get("survey_answers"), str) \
            else body.get("survey_answers") or {}
    except (json.JSONDecodeError, TypeError):
        overrides = {}

    survey_answers = {**defaults, **overrides}

    # Resolve build_task_id for deploy-type templates:
    # priority: request body → token survey_defaults["_build_task_id"]
    build_task_id: str | None = (
        body.get("build_task_id")
        or (defaults.get("_build_task_id") if isinstance(defaults.get("_build_task_id"), str) else None)
    )

    if template.type == "deploy" and not build_task_id:
        raise HTTPError(
            400,
            "build_task_id is required for deploy templates. "
            "Pass it in the request body: {\"build_task_id\": \"<task_id>\"}"
        )

    task = create_task(
        template       = template,
        user           = None,
        survey_answers = survey_answers or None,
        triggered_by   = "token",
        trigger_name   = tt.name,
        build_task_id  = build_task_id,
    )
    enqueue_task(task)

    return {
        "task_id":     str(task.id),
        "template":    template.name,
        "status":      task.status,
        "project_id":  str(template.project.id),
    }, 201


@bp.get("/api/execute/<raw_token>/<task_id>")
def execute_status(raw_token: str, task_id: str):
    """Poll the status of a task that was triggered via an execute token.

    The token is used for authentication — no user session required.
    The task must belong to the same project as the token.

    Example::

        curl "http://host/api/execute/<token>/<task_id>"

    Returns task status, timing, exit code, version and a short log excerpt.
    """
    from app.models.template_token import TemplateToken
    from app.models.task import Task

    token_hash = _hash_token(raw_token)
    tt = TemplateToken.objects(token_hash=token_hash, active=True).first()

    if not tt:
        raise HTTPError(401, "Invalid or revoked execute token")

    if tt.expires_at and tt.expires_at < datetime.datetime.utcnow():
        raise HTTPError(401, "Execute token has expired")

    try:
        task = Task.objects.get(id=task_id, project=tt.project)
    except Task.DoesNotExist:
        raise HTTPError(404, "Task not found")

    # Include last 50 log lines if available
    log_tail: str | None = None
    try:
        from app.models.task_log import TaskLog
        tl = TaskLog.objects(task=task).first()
        if tl and tl.output:
            lines = tl.output.splitlines()
            log_tail = "\n".join(lines[-50:])
    except Exception:
        pass

    return {
        "task_id":    str(task.id),
        "template":   task.template.name if task.template else None,
        "status":     task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "start":      task.start.isoformat() if task.start else None,
        "end":        task.end.isoformat() if task.end else None,
        "exit_code":  task.exit_code,
        "version":    task.version or None,
        "commit_hash":task.commit_hash or None,
        "log_tail":   log_tail,
    }, 200
