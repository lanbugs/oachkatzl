from __future__ import annotations

import json

from apiflask import APIBlueprint, HTTPError

from app.schemas.access_key import AccessKeyIn, AccessKeyOut
from app.services.rbac import require_project_role
from flask import g

bp = APIBlueprint("keys", __name__, url_prefix="/api/projects/<project_id>/keys")


def _key_out(k) -> dict:
    return {
        "id": str(k.id),
        "name": k.name,
        "type": k.type,
        "created_at": k.created_at.isoformat() if k.created_at else None,
        "has_secret": bool(k.secret),
    }


def _build_secret(key_type: str, body: dict) -> str:
    from app.services.crypto import encrypt
    if key_type == "ssh":
        return encrypt(json.dumps({
            "private_key": body.get("private_key") or "",
            "passphrase": body.get("passphrase") or "",
        }))
    if key_type == "ssh_login":
        return encrypt(json.dumps({
            "private_key": body.get("private_key") or "",
            "passphrase": body.get("passphrase") or "",
            "login": body.get("login") or "",
        }))
    if key_type == "ssh_become":
        return encrypt(json.dumps({
            "private_key": body.get("private_key") or "",
            "passphrase": body.get("passphrase") or "",
            "login": body.get("login") or "",
            "become_password": body.get("become_password") or "",
        }))
    if key_type == "login_password":
        return encrypt(json.dumps({
            "login": body.get("login") or "",
            "password": body.get("password") or "",
        }))
    if key_type == "vault":
        return encrypt(json.dumps({"vault_password": body.get("vault_password") or ""}))
    return ""


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(AccessKeyOut(many=True))
def list_keys(project_id):
    from app.models.access_key import AccessKey
    return [_key_out(k) for k in AccessKey.objects(project=g.project)]


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(AccessKeyIn, arg_name="body")
@bp.output(AccessKeyOut, status_code=201)
def create_key(project_id, body):
    from app.models.access_key import AccessKey
    secret = _build_secret(body["type"], body)
    key = AccessKey(project=g.project, name=body["name"], type=body["type"], secret=secret).save()
    return _key_out(key)


@bp.get("/<key_id>")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(AccessKeyOut)
def get_key(project_id, key_id):
    from app.models.access_key import AccessKey
    try:
        return _key_out(AccessKey.objects.get(id=key_id, project=g.project))
    except AccessKey.DoesNotExist:
        raise HTTPError(404, "Key not found")


def _has_new_secret(key_type: str, body: dict) -> bool:
    """Return True if the request contains at least one non-empty secret field."""
    if key_type in ("ssh", "ssh_login", "ssh_become"):
        return bool(body.get("private_key"))
    if key_type == "login_password":
        return bool(body.get("login") or body.get("password"))
    if key_type == "vault":
        return bool(body.get("vault_password"))
    return False


@bp.put("/<key_id>")
@require_project_role("owner", "manager")
@bp.input(AccessKeyIn, arg_name="body")
@bp.output(AccessKeyOut)
def update_key(project_id, key_id, body):
    from app.models.access_key import AccessKey
    try:
        key = AccessKey.objects.get(id=key_id, project=g.project)
    except AccessKey.DoesNotExist:
        raise HTTPError(404, "Key not found")

    key.name = body["name"]
    key.type = body["type"]
    # Only overwrite the stored secret if new credentials were provided.
    # Leaving all secret fields blank keeps the existing secret intact.
    if _has_new_secret(body["type"], body):
        key.secret = _build_secret(body["type"], body)
    key.save()
    return _key_out(key)


@bp.delete("/<key_id>")
@require_project_role("owner", "manager")
def delete_key(project_id, key_id):
    from app.models.access_key import AccessKey
    try:
        AccessKey.objects.get(id=key_id, project=g.project).delete()
    except AccessKey.DoesNotExist:
        raise HTTPError(404, "Key not found")
    return {"message": "Deleted"}, 200
