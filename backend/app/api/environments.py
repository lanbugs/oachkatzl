from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import String
from apiflask.schemas import Schema
from flask import g

from app.services.rbac import require_project_role, get_current_project_role

bp = APIBlueprint("environments", __name__, url_prefix="/api/projects/<project_id>/environments")


class EnvIn(Schema):
    name = String(required=True)
    json = String(load_default="{}")
    env = String(load_default="{}")


class EnvOut(Schema):
    id = String()
    name = String()
    json = String()
    env = String()
    created_at = String()


def _out(e, role: str | None = None) -> dict:
    redact = role in ("guest", None)
    return {
        "id": str(e.id),
        "name": e.name,
        "json": "{}" if redact else e.json,
        "env": "{}" if redact else e.env,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(EnvOut(many=True))
def list_envs(project_id):
    from app.models.environment import Environment
    role = get_current_project_role()
    return [_out(e, role) for e in Environment.objects(project=g.project)]


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(EnvIn, arg_name="body")
@bp.output(EnvOut, status_code=201)
def create_env(project_id, body):
    from app.models.environment import Environment
    e = Environment(
        project=g.project, name=body["name"],
        json=body.get("json", "{}"), env=body.get("env", "{}"),
    ).save()
    role = get_current_project_role()
    return _out(e, role)


@bp.get("/<env_id>")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(EnvOut)
def get_env(project_id, env_id):
    from app.models.environment import Environment
    try:
        e = Environment.objects.get(id=env_id, project=g.project)
    except Environment.DoesNotExist:
        raise HTTPError(404, "Environment not found")
    role = get_current_project_role()
    return _out(e, role)


@bp.put("/<env_id>")
@require_project_role("owner", "manager")
@bp.input(EnvIn, arg_name="body")
@bp.output(EnvOut)
def update_env(project_id, env_id, body):
    from app.models.environment import Environment
    try:
        e = Environment.objects.get(id=env_id, project=g.project)
    except Environment.DoesNotExist:
        raise HTTPError(404, "Environment not found")
    e.name = body["name"]
    e.json = body.get("json", e.json)
    e.env = body.get("env", e.env)
    e.save()
    role = get_current_project_role()
    return _out(e, role)


@bp.delete("/<env_id>")
@require_project_role("owner", "manager")
def delete_env(project_id, env_id):
    from app.models.environment import Environment
    try:
        Environment.objects.get(id=env_id, project=g.project).delete()
    except Environment.DoesNotExist:
        raise HTTPError(404, "Environment not found")
    return {"message": "Deleted"}, 200
