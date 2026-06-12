from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from flask import g

from app.schemas.task import TaskStartIn, TaskOut, TaskLogOut
from app.services.rbac import require_project_role

bp = APIBlueprint("tasks", __name__, url_prefix="/api/projects/<project_id>/tasks")


def _task_out(t) -> dict:
    return {
        "id": str(t.id),
        "template_id": str(t.template.id),
        "template_name": t.template.name if t.template else "",
        "status": t.status,
        "debug": t.debug,
        "dry_run": t.dry_run,
        "diff": t.diff,
        "user_id":       str(t.user.id) if t.user else None,
        "username":      t.user.username if t.user else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "start": t.start.isoformat() if t.start else None,
        "end": t.end.isoformat() if t.end else None,
        "message": t.message,
        "commit_hash": t.commit_hash,
        "version":      t.version or "",
        "build_task_id": str(t.build_task.id) if t.build_task else None,
        "exit_code":    t.exit_code,
        "triggered_by": t.triggered_by or "manual",
        "trigger_name": t.trigger_name or "",
        "survey_answers":      t.survey_answers or "{}",
        "environment_override": t.environment_override or "{}",
        "arguments_override":   t.arguments_override or "[]",
    }


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
def list_tasks(project_id):
    from app.models.task import Task
    from flask import request
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (ValueError, TypeError):
        raise HTTPError(400, "Invalid pagination parameters")
    qs    = Task.objects(project=g.project).order_by("-created_at")
    total = qs.count()
    items = qs.skip((page - 1) * per_page).limit(per_page)
    return {"items": [_task_out(t) for t in items], "total": total, "page": page, "per_page": per_page}, 200


@bp.post("/")
@require_project_role("owner", "manager", "task_runner")
@bp.input(TaskStartIn, arg_name="body")
@bp.output(TaskOut, status_code=201)
def start_task(project_id, body):
    from app.models.template import Template
    from app.services.task_service import create_task, enqueue_task

    template_id = body.get("template_id")
    # template_id may also come from query string
    from flask import request
    template_id = template_id or request.args.get("template_id")
    if not template_id:
        raise HTTPError(400, "template_id required")

    try:
        template = Template.objects.get(id=template_id, project=g.project)
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")

    task = create_task(
        template=template,
        user=g.current_user,
        debug=body.get("debug", False),
        dry_run=body.get("dry_run", False),
        diff=body.get("diff", False),
        environment_override=None,
        arguments_override=None,
        survey_answers=None,
    )
    enqueue_task(task)
    return _task_out(task)


@bp.post("/<template_id>/start")
@require_project_role("owner", "manager", "task_runner")
@bp.input(TaskStartIn, arg_name="body")
@bp.output(TaskOut, status_code=201)
def start_task_by_template(project_id, template_id, body):
    from app.models.template import Template
    from app.services.task_service import create_task, enqueue_task
    import json

    try:
        template = Template.objects.get(id=template_id, project=g.project)
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")

    env_override = {}
    args_override = []
    survey = {}
    try:
        env_override = json.loads(body.get("environment_override") or "{}")
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        args_override = json.loads(body.get("arguments_override") or "[]")
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        survey = json.loads(body.get("survey_answers") or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    task = create_task(
        template=template,
        user=g.current_user,
        debug=body.get("debug", False),
        dry_run=body.get("dry_run", False),
        diff=body.get("diff", False),
        environment_override=env_override,
        arguments_override=args_override,
        survey_answers=survey,
        build_task_id=body.get("build_task_id"),
        pin_commit=body.get("pin_commit") or "",
    )
    enqueue_task(task)
    return _task_out(task)


@bp.get("/<task_id>")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(TaskOut)
def get_task(project_id, task_id):
    from app.models.task import Task
    try:
        return _task_out(Task.objects.get(id=task_id, project=g.project))
    except Task.DoesNotExist:
        raise HTTPError(404, "Task not found")


@bp.post("/<task_id>/stop")
@require_project_role("owner", "manager", "task_runner")
def stop_task(project_id, task_id):
    from app.models.task import Task
    from app.services.task_service import stop_task as _stop
    try:
        task = Task.objects.get(id=task_id, project=g.project)
    except Task.DoesNotExist:
        raise HTTPError(404, "Task not found")
    _stop(task)
    return {"message": "Stop signal sent"}, 200


@bp.get("/<task_id>/artifacts")
@require_project_role("owner", "manager", "task_runner", "guest")
def get_task_artifacts(project_id, task_id):
    from app.models.task import Task
    from app.models.artifact import Artifact
    try:
        task = Task.objects.get(id=task_id, project=g.project)
    except Task.DoesNotExist:
        raise HTTPError(404, "Task not found")
    if not task.artifact_run:
        return [], 200
    artifacts = Artifact.objects(run=task.artifact_run).order_by("-created_at")
    return [
        {
            "id":            str(a.id),
            "run_id":        str(a.run.id),
            "name":          a.name,
            "artifact_type": a.artifact_type,
            "content_type":  a.content_type or "application/octet-stream",
            "size_bytes":    a.size_bytes or 0,
            "created_at":    a.created_at.isoformat() if a.created_at else None,
        }
        for a in artifacts
    ], 200


@bp.get("/<task_id>/log")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(TaskLogOut)
def get_task_log(project_id, task_id):
    from app.models.task import Task, TaskLog
    try:
        task = Task.objects.get(id=task_id, project=g.project)
    except Task.DoesNotExist:
        raise HTTPError(404, "Task not found")

    log = TaskLog.objects(task=task).first()
    return {"task_id": task_id, "output": log.output if log else ""}
