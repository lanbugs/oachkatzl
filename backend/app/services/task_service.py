from __future__ import annotations

import json
import re

from apiflask import HTTPError

from app.models.task import Task
from app.models.template import Template
from app.models.project import Project

VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')


def _next_build_version(template: Template) -> str:
    """Increment the patch component of the last successful build version."""
    last = Task.objects(template=template, status="success").order_by("-created_at").first()
    if last and last.version and VERSION_RE.match(last.version):
        major, minor, patch = last.version.split(".")
        return f"{major}.{minor}.{int(patch) + 1}"
    return template.start_version or "1.0.0"


def create_task(
    template: Template,
    user=None,
    debug: bool = False,
    dry_run: bool = False,
    diff: bool = False,
    environment_override: dict | None = None,
    arguments_override: list | None = None,
    survey_answers: dict | None = None,
    triggered_by: str = "manual",
    trigger_name: str = "",
    build_task_id: str | None = None,   # for deploy-type tasks
    pin_commit: str = "",               # replay: pin to a specific git commit
    artifact_run=None,                  # pre-created ArtifactRun (workflow shared token)
) -> Task:
    task = Task(
        project=template.project,
        template=template,
        status="waiting",
        debug=debug,
        dry_run=dry_run,
        diff=diff,
        user=user,
        environment_override=json.dumps(environment_override or {}),
        arguments_override=json.dumps(arguments_override or []),
        survey_answers=json.dumps(survey_answers or {}),
        triggered_by=triggered_by,
        trigger_name=trigger_name,
        pin_commit=pin_commit,
    )
    if artifact_run is not None:
        task.artifact_run = artifact_run

    # Build: auto-assign next version
    if template.type == "build" and template.start_version:
        task.version = _next_build_version(template)

    # Deploy: link to the chosen build task and inherit its version
    if template.type == "deploy" and build_task_id:
        try:
            build_task = Task.objects.get(id=build_task_id, project=template.project)
            task.build_task = build_task
            task.version    = build_task.version
        except Task.DoesNotExist:
            raise HTTPError(404, f"Build task {build_task_id} not found")

    task.save()
    return task


def enqueue_task(task: Task) -> None:
    """Send task to Celery queue."""
    from app.tasks.run_task import run_task
    run_task.delay(str(task.id))


def stop_task(task: Task) -> None:
    """Signal a running task to stop via Redis flag."""
    import redis as redis_lib
    from app.config import settings

    if task.status not in ("waiting", "starting", "running"):
        raise HTTPError(400, f"Cannot stop task with status '{task.status}'")

    if task.status == "waiting":
        task.status = "stopped"
        task.save()
        return

    r = redis_lib.from_url(settings.REDIS_URL)
    r.set(f"stop:{task.id}", "1", ex=300)
