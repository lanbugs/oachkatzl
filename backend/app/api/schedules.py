from __future__ import annotations

import json

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Boolean, String
from apiflask.schemas import Schema
from flask import g

from app.services.rbac import require_project_role

bp = APIBlueprint("schedules", __name__, url_prefix="/api/projects/<project_id>/schedules")


class ScheduleIn(Schema):
    # Exactly one of template_id / workflow_id must be provided.
    template_id    = String(load_default=None)
    workflow_id    = String(load_default=None)
    cron_format    = String(required=True)
    active         = Boolean(load_default=True)
    survey_answers = String(load_default="{}")


class ScheduleOut(Schema):
    id            = String()
    type          = String()   # "template" | "workflow"
    template_id   = String()
    template_name = String()
    workflow_id   = String()
    workflow_name = String()
    cron_format   = String()
    active        = Boolean()
    survey_answers = String()
    created_at    = String()


def _out(s) -> dict:
    is_wf = bool(s.workflow)
    return {
        "id":             str(s.id),
        "type":           "workflow" if is_wf else "template",
        "template_id":    str(s.template.id)  if s.template else None,
        "template_name":  s.template.name      if s.template else None,
        "workflow_id":    str(s.workflow.id)   if s.workflow else None,
        "workflow_name":  s.workflow.name      if s.workflow else None,
        "cron_format":    s.cron_format,
        "active":         s.active,
        "survey_answers": s.survey_answers or "{}",
        "created_at":     s.created_at.isoformat() if s.created_at else None,
    }


def _resolve_refs(body: dict, project):
    """Return (template, workflow). Exactly one must be non-None."""
    from app.models.template import Template
    from app.models.workflow import WorkflowTemplate

    tid = body.get("template_id")
    wid = body.get("workflow_id")

    if tid and wid:
        raise HTTPError(400, "Provide either template_id or workflow_id, not both")
    if not tid and not wid:
        raise HTTPError(400, "Either template_id or workflow_id is required")

    template = workflow = None
    if tid:
        try:
            template = Template.objects.get(id=tid, project=project)
        except Template.DoesNotExist:
            raise HTTPError(404, "Template not found")
    else:
        try:
            workflow = WorkflowTemplate.objects.get(id=wid, project=project)
        except WorkflowTemplate.DoesNotExist:
            raise HTTPError(404, "Workflow not found")

    return template, workflow


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

    template, workflow = _resolve_refs(body, g.project)

    survey_answers = body.get("survey_answers", "{}")
    try:
        json.loads(survey_answers)
    except (json.JSONDecodeError, TypeError):
        survey_answers = "{}"

    s = Schedule(
        project=g.project,
        template=template,
        workflow=workflow,
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

    try:
        s = Schedule.objects.get(id=sched_id, project=g.project)
    except Schedule.DoesNotExist:
        raise HTTPError(404, "Schedule not found")

    template, workflow = _resolve_refs(body, g.project)
    s.template = template
    s.workflow  = workflow
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
