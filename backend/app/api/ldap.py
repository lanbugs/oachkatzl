from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Boolean, List, String
from apiflask.schemas import Schema
from marshmallow import fields as ma_fields, validate

from app.models.project import ROLES
from app.services.rbac import require_admin

bp = APIBlueprint("ldap", __name__, url_prefix="/api/ldap")


# ── Schemas ───────────────────────────────────────────────────────────────

class LdapConfigIn(Schema):
    enabled                = Boolean(load_default=False)
    server_url             = String(load_default="")
    use_tls                = Boolean(load_default=False)
    use_ssl                = Boolean(load_default=False)
    bind_dn                = String(load_default="")
    bind_password          = String(load_default=None)   # None → don't change
    base_dn                = String(load_default="")
    user_search_filter     = String(load_default="(sAMAccountName={username})")
    group_membership_attr  = String(load_default="memberOf")
    follow_nested_groups   = Boolean(load_default=False)
    attr_email             = String(load_default="mail")
    attr_display_name      = String(load_default="displayName")
    attr_uid               = String(load_default="objectGUID")
    admin_groups           = List(String(), load_default=[])


class LdapGroupMappingIn(Schema):
    group_dn   = String(required=True)
    project_id = String(required=True)
    role       = String(required=True, validate=validate.OneOf(ROLES))


# ── Helper ────────────────────────────────────────────────────────────────

def _cfg_out(cfg) -> dict:
    return {
        "enabled":               cfg.enabled,
        "server_url":            cfg.server_url,
        "use_tls":               cfg.use_tls,
        "use_ssl":               cfg.use_ssl,
        "bind_dn":               cfg.bind_dn,
        "bind_password_set":     bool(cfg.bind_password_enc),
        "base_dn":               cfg.base_dn,
        "user_search_filter":    cfg.user_search_filter,
        "group_membership_attr": cfg.group_membership_attr,
        "follow_nested_groups":  cfg.follow_nested_groups,
        "attr_email":            cfg.attr_email,
        "attr_display_name":     cfg.attr_display_name,
        "attr_uid":              cfg.attr_uid,
        "admin_groups":          list(cfg.admin_groups or []),
    }


def _mapping_out(m) -> dict:
    try:
        project_name = m.project.name
        project_id   = str(m.project.id)
    except Exception:
        project_name = ""
        project_id   = ""
    return {
        "id":           str(m.id),
        "group_dn":     m.group_dn,
        "project_id":   project_id,
        "project_name": project_name,
        "role":         m.role,
    }


# ── Config endpoints ──────────────────────────────────────────────────────

@bp.get("/config")
@require_admin
def get_config():
    from app.models.ldap_config import LdapConfig
    cfg = LdapConfig.objects.first()
    if cfg is None:
        cfg = LdapConfig()   # return empty defaults without saving
    return _cfg_out(cfg), 200


@bp.put("/config")
@require_admin
@bp.input(LdapConfigIn, arg_name="body")
def save_config(body):
    from app.models.ldap_config import LdapConfig
    from app.services.crypto import encrypt

    cfg = LdapConfig.objects.first()
    if cfg is None:
        cfg = LdapConfig()

    cfg.enabled               = body.get("enabled", cfg.enabled)
    cfg.server_url            = body.get("server_url", cfg.server_url)
    cfg.use_tls               = body.get("use_tls", cfg.use_tls)
    cfg.use_ssl               = body.get("use_ssl", cfg.use_ssl)
    cfg.bind_dn               = body.get("bind_dn", cfg.bind_dn)
    cfg.base_dn               = body.get("base_dn", cfg.base_dn)
    cfg.user_search_filter    = body.get("user_search_filter", cfg.user_search_filter)
    cfg.group_membership_attr = body.get("group_membership_attr", cfg.group_membership_attr)
    cfg.follow_nested_groups  = body.get("follow_nested_groups", cfg.follow_nested_groups)
    cfg.attr_email            = body.get("attr_email", cfg.attr_email)
    cfg.attr_display_name     = body.get("attr_display_name", cfg.attr_display_name)
    cfg.attr_uid              = body.get("attr_uid", cfg.attr_uid)
    # Normalize admin_groups to lowercase for case-insensitive matching
    raw_admin = body.get("admin_groups", cfg.admin_groups or [])
    cfg.admin_groups          = [g.strip().lower() for g in raw_admin if g.strip()]

    # Only update password when explicitly provided
    new_pw = body.get("bind_password")
    if new_pw is not None:
        cfg.bind_password_enc = encrypt(new_pw)

    cfg.save()
    return _cfg_out(cfg), 200


# ── Test connection ───────────────────────────────────────────────────────

@bp.post("/test")
@require_admin
def test_connection():
    from app.services.ldap_service import test_ldap_connection
    result = test_ldap_connection()
    status = 200 if result["ok"] else 502
    return result, status


# ── Group mappings ────────────────────────────────────────────────────────

@bp.get("/mappings")
@require_admin
def list_mappings():
    from app.models.ldap_config import LdapGroupMapping
    return [_mapping_out(m) for m in LdapGroupMapping.objects.all()], 200


@bp.post("/mappings")
@require_admin
@bp.input(LdapGroupMappingIn, arg_name="body")
def create_mapping(body):
    from app.models.ldap_config import LdapGroupMapping
    from app.models.project import Project

    try:
        project = Project.objects.get(id=body["project_id"])
    except Project.DoesNotExist:
        raise HTTPError(404, "Project not found")

    group_dn = body["group_dn"].strip().lower()
    if not group_dn:
        raise HTTPError(400, "group_dn is required")

    # Prevent duplicate (group_dn, project) pairs
    if LdapGroupMapping.objects(group_dn=group_dn, project=project).first():
        raise HTTPError(409, "Mapping already exists for this group and project")

    m = LdapGroupMapping(
        group_dn = group_dn,
        project  = project,
        role     = body["role"],
    ).save()
    return _mapping_out(m), 201


@bp.delete("/mappings/<mapping_id>")
@require_admin
def delete_mapping(mapping_id):
    from app.models.ldap_config import LdapGroupMapping
    try:
        LdapGroupMapping.objects.get(id=mapping_id).delete()
    except LdapGroupMapping.DoesNotExist:
        raise HTTPError(404, "Mapping not found")
    return {"message": "Deleted"}, 200
