from __future__ import annotations

import json

from apiflask import APIBlueprint, HTTPError
from flask import g

from app.schemas.credential import CredentialIn, CredentialOut
from app.services.rbac import require_project_role

bp = APIBlueprint("credentials", __name__, url_prefix="/api/projects/<project_id>/credentials")


def _cred_out(c) -> dict:
    filled: list[str] = []
    if c.inputs:
        try:
            from app.services.crypto import decrypt
            data = json.loads(decrypt(c.inputs))
            filled = [k for k, v in data.items() if v]
        except Exception:
            pass
    return {
        "id":                   str(c.id),
        "name":                 c.name,
        "credential_type_id":   str(c.credential_type.id),
        "credential_type_name": c.credential_type.name if c.credential_type else "",
        "filled_fields":        filled,
        "created_at":           c.created_at.isoformat() if c.created_at else None,
    }


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
def list_credentials(project_id):
    from app.models.credential import Credential
    return [_cred_out(c) for c in Credential.objects(project=g.project).order_by("name")], 200


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(CredentialIn, arg_name="body")
@bp.output(CredentialOut, status_code=201)
def create_credential(project_id, body):
    from app.models.credential import Credential
    from app.models.credential_type import CredentialType
    from app.services.crypto import encrypt

    try:
        ct = CredentialType.objects.get(id=body["credential_type_id"])
    except CredentialType.DoesNotExist:
        raise HTTPError(404, "Credential type not found")

    inputs_raw = body.get("inputs", "{}")
    try:
        inputs_dict = json.loads(inputs_raw)
    except (json.JSONDecodeError, TypeError):
        inputs_dict = {}

    c = Credential(
        project=g.project,
        name=body["name"],
        credential_type=ct,
        inputs=encrypt(json.dumps(inputs_dict)) if inputs_dict else "",
    ).save()
    return _cred_out(c)


@bp.get("/<cred_id>")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(CredentialOut)
def get_credential(project_id, cred_id):
    from app.models.credential import Credential
    try:
        return _cred_out(Credential.objects.get(id=cred_id, project=g.project))
    except Credential.DoesNotExist:
        raise HTTPError(404, "Credential not found")


@bp.put("/<cred_id>")
@require_project_role("owner", "manager")
@bp.input(CredentialIn, arg_name="body")
@bp.output(CredentialOut)
def update_credential(project_id, cred_id, body):
    from app.models.credential import Credential
    from app.models.credential_type import CredentialType
    from app.services.crypto import encrypt, decrypt

    try:
        c = Credential.objects.get(id=cred_id, project=g.project)
    except Credential.DoesNotExist:
        raise HTTPError(404, "Credential not found")

    if body.get("credential_type_id"):
        try:
            c.credential_type = CredentialType.objects.get(id=body["credential_type_id"])
        except CredentialType.DoesNotExist:
            raise HTTPError(404, "Credential type not found")

    c.name = body["name"]

    # Merge: load existing, overlay non-empty incoming values
    existing: dict = {}
    if c.inputs:
        try:
            existing = json.loads(decrypt(c.inputs))
        except Exception:
            pass

    try:
        incoming = json.loads(body.get("inputs", "{}"))
    except (json.JSONDecodeError, TypeError):
        incoming = {}

    for k, v in incoming.items():
        if v:   # only overwrite when a non-empty value is provided
            existing[k] = v

    c.inputs = encrypt(json.dumps(existing)) if existing else ""
    c.save()
    return _cred_out(c)


@bp.delete("/<cred_id>")
@require_project_role("owner", "manager")
def delete_credential(project_id, cred_id):
    from app.models.credential import Credential
    try:
        Credential.objects.get(id=cred_id, project=g.project).delete()
    except Credential.DoesNotExist:
        raise HTTPError(404, "Credential not found")
    return {"message": "Deleted"}, 200
