from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from flask import g

from app.schemas.credential import CredentialTypeIn, CredentialTypeOut
from app.services.rbac import require_admin

bp = APIBlueprint("credential_types", __name__, url_prefix="/api/credential-types")


def _ct_out(ct) -> dict:
    return {
        "id":          str(ct.id),
        "name":        ct.name,
        "description": ct.description,
        "inputs":      ct.inputs or "[]",
        "injectors":   ct.injectors or "{}",
        "created_at":  ct.created_at.isoformat() if ct.created_at else None,
    }


@bp.get("/")
def list_credential_types():
    from app.models.credential_type import CredentialType
    return [_ct_out(ct) for ct in CredentialType.objects.order_by("name")], 200


@bp.post("/")
@require_admin
@bp.input(CredentialTypeIn, arg_name="body")
@bp.output(CredentialTypeOut, status_code=201)
def create_credential_type(body):
    from app.models.credential_type import CredentialType
    ct = CredentialType(
        name=body["name"],
        description=body.get("description", ""),
        inputs=body.get("inputs", "[]"),
        injectors=body.get("injectors", "{}"),
    ).save()
    return _ct_out(ct)


@bp.put("/<ct_id>")
@require_admin
@bp.input(CredentialTypeIn, arg_name="body")
@bp.output(CredentialTypeOut)
def update_credential_type(ct_id, body):
    from app.models.credential_type import CredentialType
    try:
        ct = CredentialType.objects.get(id=ct_id)
    except CredentialType.DoesNotExist:
        raise HTTPError(404, "Credential type not found")
    ct.name        = body["name"]
    ct.description = body.get("description", "")
    ct.inputs      = body.get("inputs", "[]")
    ct.injectors   = body.get("injectors", "{}")
    ct.save()
    return _ct_out(ct)


@bp.delete("/<ct_id>")
@require_admin
def delete_credential_type(ct_id):
    from app.models.credential_type import CredentialType
    try:
        CredentialType.objects.get(id=ct_id).delete()
    except CredentialType.DoesNotExist:
        raise HTTPError(404, "Credential type not found")
    return {"message": "Deleted"}, 200
