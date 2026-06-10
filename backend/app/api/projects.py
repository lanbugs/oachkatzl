from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from flask import g, request

from app.schemas.project import ProjectIn, ProjectOut, MemberIn, MemberOut
from app.services.rbac import require_auth, require_admin, require_project_role

bp = APIBlueprint("projects", __name__, url_prefix="/api/projects")


def _project_out(p) -> dict:
    return {
        "id": str(p.id),
        "name": p.name,
        "alert": p.alert,
        "max_parallel_tasks": p.max_parallel_tasks,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "demo": p.demo,
    }


@bp.get("/")
@require_auth
@bp.output(ProjectOut(many=True))
def list_projects():
    from app.models.project import Project, ProjectMember
    if g.current_user.is_admin:
        return [_project_out(p) for p in Project.objects.all()]
    memberships = ProjectMember.objects(user=g.current_user)
    return [_project_out(m.project) for m in memberships]


@bp.post("/")
@require_admin
@bp.input(ProjectIn, arg_name="body")
@bp.output(ProjectOut, status_code=201)
def create_project(body):
    from app.models.project import Project, ProjectMember
    project = Project(
        name=body["name"],
        alert=body.get("alert", True),
        max_parallel_tasks=body.get("max_parallel_tasks", 0),
    ).save()
    ProjectMember(project=project, user=g.current_user, role="owner").save()
    return _project_out(project)


@bp.get("/<project_id>")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(ProjectOut)
def get_project(project_id):
    return _project_out(g.project)


@bp.put("/<project_id>")
@require_project_role("owner", "manager")
@bp.input(ProjectIn, arg_name="body")
@bp.output(ProjectOut)
def update_project(project_id, body):
    p = g.project
    p.name = body["name"]
    p.alert = body.get("alert", p.alert)
    p.max_parallel_tasks = body.get("max_parallel_tasks", p.max_parallel_tasks)
    p.save()
    return _project_out(p)


@bp.delete("/<project_id>")
@require_project_role("owner")
def delete_project(project_id):
    from app.models.project import ProjectMember
    ProjectMember.objects(project=g.project).delete()
    g.project.delete()
    return {"message": "Deleted"}, 200


# ── Members ───────────────────────────────────────────────────────────────

@bp.get("/<project_id>/members")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(MemberOut(many=True))
def list_members(project_id):
    from app.models.project import ProjectMember
    members = ProjectMember.objects(project=g.project)
    return [
        {
            "id":       str(m.id),
            "user_id":  str(m.user.id),
            "username": m.user.username,
            "email":    m.user.email,
            "role":     m.role,
            "source":   m.source or "manual",
        }
        for m in members
    ]


@bp.post("/<project_id>/members")
@require_project_role("owner", "manager")
@bp.input(MemberIn, arg_name="body")
@bp.output(MemberOut, status_code=201)
def add_member(project_id, body):
    from app.models.project import ProjectMember
    from app.models.user import User
    try:
        user = User.objects.get(id=body["user_id"])
    except User.DoesNotExist:
        raise HTTPError(404, "User not found")

    if ProjectMember.objects(project=g.project, user=user).first():
        raise HTTPError(409, "Already a member")

    m = ProjectMember(project=g.project, user=user, role=body["role"], source="manual").save()
    return {"id": str(m.id), "user_id": str(user.id), "username": user.username, "email": user.email, "role": m.role, "source": "manual"}


@bp.put("/<project_id>/members/<member_id>")
@require_project_role("owner", "manager")
@bp.input(MemberIn, arg_name="body")
@bp.output(MemberOut)
def update_member(project_id, member_id, body):
    from app.models.project import ProjectMember
    try:
        m = ProjectMember.objects.get(id=member_id, project=g.project)
    except ProjectMember.DoesNotExist:
        raise HTTPError(404, "Member not found")
    m.role   = body["role"]
    m.source = "manual"   # editing via UI always makes it a manual entry
    m.save()
    return {"id": str(m.id), "user_id": str(m.user.id), "username": m.user.username, "email": m.user.email, "role": m.role, "source": m.source}


@bp.delete("/<project_id>/members/<member_id>")
@require_project_role("owner", "manager")
def remove_member(project_id, member_id):
    from app.models.project import ProjectMember
    try:
        ProjectMember.objects.get(id=member_id, project=g.project).delete()
    except ProjectMember.DoesNotExist:
        raise HTTPError(404, "Member not found")
    return {"message": "Removed"}, 200


# ── LDAP group mappings for this project ──────────────────────────────────

@bp.get("/<project_id>/ldap-mappings")
@require_project_role("owner", "manager")
def list_project_ldap_mappings(project_id):
    """Return LDAP group mappings that target this project."""
    try:
        from app.models.ldap_config import LdapGroupMapping
    except ImportError:
        return [], 200
    mappings = LdapGroupMapping.objects(project=g.project)
    return [
        {
            "id":       str(m.id),
            "group_dn": m.group_dn,
            "role":     m.role,
        }
        for m in mappings
    ], 200


# ── Direct LDAP user → project role mappings ──────────────────────────────

@bp.get("/<project_id>/ldap-user-mappings")
@require_project_role("owner", "manager")
def list_ldap_user_mappings(project_id):
    try:
        from app.models.ldap_config import LdapUserMapping
    except ImportError:
        return [], 200
    mappings = LdapUserMapping.objects(project=g.project)
    return [
        {"id": str(m.id), "ldap_username": m.ldap_username, "role": m.role}
        for m in mappings
    ], 200


@bp.post("/<project_id>/ldap-user-mappings")
@require_project_role("owner", "manager")
def create_ldap_user_mapping(project_id):
    from app.models.ldap_config import LdapUserMapping
    from app.models.project import ROLES
    body = request.get_json(force=True, silent=True) or {}
    username = (body.get("ldap_username") or "").strip().lower()
    role     = body.get("role", "")
    if not username:
        raise HTTPError(400, "ldap_username is required")
    if role not in ROLES:
        raise HTTPError(400, f"role must be one of {ROLES}")
    if LdapUserMapping.objects(ldap_username=username, project=g.project).first():
        raise HTTPError(409, "Mapping already exists for this user and project")
    m = LdapUserMapping(ldap_username=username, project=g.project, role=role).save()
    return {"id": str(m.id), "ldap_username": m.ldap_username, "role": m.role}, 201


@bp.delete("/<project_id>/ldap-user-mappings/<mapping_id>")
@require_project_role("owner", "manager")
def delete_ldap_user_mapping(project_id, mapping_id):
    from app.models.ldap_config import LdapUserMapping
    try:
        LdapUserMapping.objects.get(id=mapping_id, project=g.project).delete()
    except LdapUserMapping.DoesNotExist:
        raise HTTPError(404, "Mapping not found")
    return {"message": "Deleted"}, 200
