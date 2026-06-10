from __future__ import annotations

import json

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Boolean, String
from apiflask.schemas import Schema
from flask import g

from app.services.rbac import require_project_role

bp = APIBlueprint("schedules", __name__, url_prefix="/api/projects/<project_id>/schedules")


class ScheduleIn(Schema):
    template_id = String(required=True)
    cron_format = String(required=True)
    active = Boolean(load_default=True)
    survey_answers = String(load_default="{}")   # JSON dict of pre-filled survey values


class ScheduleOut(Schema):
    id = String()
    template_id = String()
    cron_format = String()
    active = Boolean()
    survey_answers = String()
    created_at = String()


def _out(s) -> dict:
    return {
        "id": str(s.id),
        "template_id": str(s.template.id),
        "cron_format": s.cron_format,
        "active": s.active,
        "survey_answers": s.survey_answers or "{}",
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(ScheduleOut(many=True))
def list_schedules(project_id):
    from app.models.schedule import Schedule
    return [_out(s) for s in Schedule.objects(project=g.project)]


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(ScheduleIn, arg_name="body")
@bp.output(ScheduleOut, status_code=201)
def create_schedule(project_id, body):
    from app.models.schedule import Schedule
    from app.models.template import Template
    try:
        tmpl = Template.objects.get(id=body["template_id"], project=g.project)
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")

    survey_answers = body.get("survey_answers", "{}")
    # Validate JSON
    try:
        json.loads(survey_answers)
    except (json.JSONDecodeError, TypeError):
        survey_answers = "{}"

    s = Schedule(
        project=g.project,
        template=tmpl,
        cron_format=body["cron_format"],
        active=body.get("active", True),
        survey_answers=survey_answers,
    ).save()
    return _out(s)


@bp.put("/<sched_id>")
@require_project_role("owner", "manager")
@bp.input(ScheduleIn, arg_name="body")
@bp.output(ScheduleOut)
def update_schedule(project_id, sched_id, body):
    from app.models.schedule import Schedule
    from app.models.template import Template
    try:
        s = Schedule.objects.get(id=sched_id, project=g.project)
    except Schedule.DoesNotExist:
        raise HTTPError(404, "Schedule not found")

    # Update template if supplied (and it belongs to the same project)
    if body.get("template_id"):
        try:
            s.template = Template.objects.get(id=body["template_id"], project=g.project)
        except Template.DoesNotExist:
            raise HTTPError(404, "Template not found")

    s.cron_format = body["cron_format"]
    s.active = body.get("active", s.active)

    survey_answers = body.get("survey_answers", s.survey_answers or "{}")
    try:
        json.loads(survey_answers)
        s.survey_answers = survey_answers
    except (json.JSONDecodeError, TypeError):
        pass

    s.save()
    return _out(s)


@bp.delete("/<sched_id>")
@require_project_role("owner", "manager")
def delete_schedule(project_id, sched_id):
    from app.models.schedule import Schedule
    try:
        Schedule.objects.get(id=sched_id, project=g.project).delete()
    except Schedule.DoesNotExist:
        raise HTTPError(404, "Schedule not found")
    return {"message": "Deleted"}, 200
