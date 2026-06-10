from __future__ import annotations

from apiflask import APIBlueprint
from flask import g

from app.services.rbac import require_project_role

bp = APIBlueprint("backup", __name__, url_prefix="/api/projects/<project_id>/backup")


@bp.get("/export")
@require_project_role("owner")
def export_project(project_id):
    from app.models.template import Template
    from app.models.inventory import Inventory
    from app.models.environment import Environment
    from app.models.repository import Repository
    from app.models.access_key import AccessKey
    from app.models.schedule import Schedule
    from app.models.view import View

    project = g.project

    def _repo_out(r):
        return {"name": r.name, "git_url": r.git_url, "git_branch": r.git_branch}

    def _key_out(k):
        return {"name": k.name, "type": k.type}  # no secrets

    def _inv_out(inv):
        return {"name": inv.name, "type": inv.type, "inventory": inv.inventory}

    def _env_out(e):
        return {"name": e.name, "json": "{}", "env": "{}"}

    def _tmpl_out(t):
        return {
            "name": t.name, "description": t.description, "app": t.app,
            "type": t.type, "playbook": t.playbook,
            "arguments": t.arguments,
            "survey_vars": [
                {"name": sv.name, "type": sv.type, "required": sv.required}
                for sv in t.survey_vars
            ],
        }

    data = {
        "project": {"name": project.name},
        "repositories": [_repo_out(r) for r in Repository.objects(project=project)],
        "access_keys": [_key_out(k) for k in AccessKey.objects(project=project)],
        "inventories": [_inv_out(i) for i in Inventory.objects(project=project)],
        "environments": [_env_out(e) for e in Environment.objects(project=project)],
        "templates": [_tmpl_out(t) for t in Template.objects(project=project)],
        "schedules": [
            {"cron_format": s.cron_format, "active": s.active}
            for s in Schedule.objects(project=project)
        ],
    }
    return data, 200
