from __future__ import annotations

import json

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Boolean, String
from apiflask.schemas import Schema
from marshmallow import validate
from flask import g

from app.services.rbac import require_project_role, require_admin, require_auth

bp = APIBlueprint("notifications", __name__)

CHANNELS = ("email", "slack", "telegram", "teams", "gotify")
SCOPES   = ("global", "project")


class NotifIn(Schema):
    channel    = String(required=True, validate=validate.OneOf(CHANNELS))
    config     = String(load_default="{}")   # JSON: channel-specific settings
    on_success = Boolean(load_default=False)
    on_failure = Boolean(load_default=True)


class NotifOut(Schema):
    id         = String()
    scope      = String()
    channel    = String()
    config     = String()
    on_success = Boolean()
    on_failure = Boolean()


class TestIn(Schema):
    channel = String(required=True, validate=validate.OneOf(CHANNELS))
    config  = String(required=True)


def _out(n) -> dict:
    return {
        "id":         str(n.id),
        "scope":      n.scope,
        "channel":    n.channel,
        "config":     n.config or "{}",
        "on_success": n.on_success,
        "on_failure": n.on_failure,
    }


# ── Per-project notifications ─────────────────────────────────────────────

@bp.get("/api/projects/<project_id>/notifications")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(NotifOut(many=True))
def list_project_notifs(project_id):
    from app.models.notification import NotificationSetting
    return [_out(n) for n in NotificationSetting.objects(scope="project", project=g.project)]


@bp.post("/api/projects/<project_id>/notifications")
@require_project_role("owner", "manager")
@bp.input(NotifIn, arg_name="body")
@bp.output(NotifOut, status_code=201)
def create_project_notif(project_id, body):
    from app.models.notification import NotificationSetting
    _validate_config(body["channel"], body.get("config", "{}"))
    n = NotificationSetting(
        scope="project",
        project=g.project,
        channel=body["channel"],
        config=body.get("config", "{}"),
        on_success=body.get("on_success", False),
        on_failure=body.get("on_failure", True),
    ).save()
    return _out(n)


@bp.put("/api/projects/<project_id>/notifications/<notif_id>")
@require_project_role("owner", "manager")
@bp.input(NotifIn, arg_name="body")
@bp.output(NotifOut)
def update_project_notif(project_id, notif_id, body):
    from app.models.notification import NotificationSetting
    try:
        n = NotificationSetting.objects.get(id=notif_id, scope="project", project=g.project)
    except NotificationSetting.DoesNotExist:
        raise HTTPError(404, "Notification not found")
    _validate_config(body["channel"], body.get("config", "{}"))
    n.channel    = body["channel"]
    n.config     = body.get("config", n.config)
    n.on_success = body.get("on_success", n.on_success)
    n.on_failure = body.get("on_failure", n.on_failure)
    n.save()
    return _out(n)


@bp.delete("/api/projects/<project_id>/notifications/<notif_id>")
@require_project_role("owner", "manager")
def delete_project_notif(project_id, notif_id):
    from app.models.notification import NotificationSetting
    try:
        NotificationSetting.objects.get(id=notif_id, scope="project", project=g.project).delete()
    except NotificationSetting.DoesNotExist:
        raise HTTPError(404, "Notification not found")
    return {"message": "Deleted"}, 200


@bp.post("/api/projects/<project_id>/notifications/test")
@require_project_role("owner", "manager")
@bp.input(TestIn, arg_name="body")
def test_project_notif(project_id, body):
    _send_test(body["channel"], body["config"])
    return {"message": "Test notification sent"}, 200


# ── Global notifications (admin) ──────────────────────────────────────────

@bp.get("/api/notifications")
@require_admin
@bp.output(NotifOut(many=True))
def list_global_notifs():
    from app.models.notification import NotificationSetting
    return [_out(n) for n in NotificationSetting.objects(scope="global")]


@bp.post("/api/notifications")
@require_admin
@bp.input(NotifIn, arg_name="body")
@bp.output(NotifOut, status_code=201)
def create_global_notif(body):
    from app.models.notification import NotificationSetting
    _validate_config(body["channel"], body.get("config", "{}"))
    n = NotificationSetting(
        scope="global",
        channel=body["channel"],
        config=body.get("config", "{}"),
        on_success=body.get("on_success", False),
        on_failure=body.get("on_failure", True),
    ).save()
    return _out(n)


@bp.delete("/api/notifications/<notif_id>")
@require_admin
def delete_global_notif(notif_id):
    from app.models.notification import NotificationSetting
    try:
        NotificationSetting.objects.get(id=notif_id, scope="global").delete()
    except NotificationSetting.DoesNotExist:
        raise HTTPError(404, "Notification not found")
    return {"message": "Deleted"}, 200


@bp.post("/api/notifications/test")
@require_admin
@bp.input(TestIn, arg_name="body")
def test_global_notif(body):
    _send_test(body["channel"], body["config"])
    return {"message": "Test notification sent"}, 200


# ── Helpers ───────────────────────────────────────────────────────────────

def _validate_config(channel: str, config_str: str) -> dict:
    try:
        return json.loads(config_str)
    except (json.JSONDecodeError, TypeError):
        raise HTTPError(400, f"config must be valid JSON for channel '{channel}'")


def _send_test(channel: str, config_str: str) -> None:
    """Send a test notification with a dummy task-like message."""
    import requests as req

    config = _validate_config(channel, config_str)

    class _FakeTask:
        status      = "error"
        exit_code   = 1
        commit_hash = "deadbeef"
        start       = None
        end         = None

    class _FakeTemplate:
        name = "Test notification"

    from app.services.notify_service import SENDERS
    sender = SENDERS.get(channel)
    if not sender:
        raise HTTPError(400, f"Unknown channel '{channel}'")
    try:
        sender(config, _FakeTask(), _FakeTemplate())
    except Exception as exc:
        raise HTTPError(502, f"Notification failed: {exc}") from exc
