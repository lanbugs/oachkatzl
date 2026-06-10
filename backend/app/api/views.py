from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Integer, String
from apiflask.schemas import Schema
from flask import g

from app.services.rbac import require_project_role

bp = APIBlueprint("views", __name__, url_prefix="/api/projects/<project_id>/views")


class ViewIn(Schema):
    title = String(required=True)
    position = Integer(load_default=0)


class ViewOut(Schema):
    id = String()
    title = String()
    position = Integer()


def _out(v) -> dict:
    return {"id": str(v.id), "title": v.title, "position": v.position}


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(ViewOut(many=True))
def list_views(project_id):
    from app.models.view import View
    return [_out(v) for v in View.objects(project=g.project).order_by("position")]


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(ViewIn, arg_name="body")
@bp.output(ViewOut, status_code=201)
def create_view(project_id, body):
    from app.models.view import View
    v = View(project=g.project, title=body["title"], position=body.get("position", 0)).save()
    return _out(v)


@bp.put("/<view_id>")
@require_project_role("owner", "manager")
@bp.input(ViewIn, arg_name="body")
@bp.output(ViewOut)
def update_view(project_id, view_id, body):
    from app.models.view import View
    try:
        v = View.objects.get(id=view_id, project=g.project)
    except View.DoesNotExist:
        raise HTTPError(404, "View not found")
    v.title = body["title"]
    v.position = body.get("position", v.position)
    v.save()
    return _out(v)


@bp.delete("/<view_id>")
@require_project_role("owner", "manager")
def delete_view(project_id, view_id):
    from app.models.view import View
    try:
        View.objects.get(id=view_id, project=g.project).delete()
    except View.DoesNotExist:
        raise HTTPError(404, "View not found")
    return {"message": "Deleted"}, 200
