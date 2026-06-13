"""Celery Beat task that polls active schedules and enqueues due tasks."""
from __future__ import annotations

import datetime
import json
import logging

from app.celery_app import celery

log = logging.getLogger(__name__)


def _resolve_survey_answers_from_vars(schedule, survey_vars) -> tuple[dict, list[str]]:
    """Resolve survey answers for any resource that has survey_vars."""
    stored: dict = {}
    try:
        stored = json.loads(schedule.survey_answers or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    answers: dict = {}
    missing: list[str] = []

    for sv in survey_vars:
        if sv.name in stored and stored[sv.name] not in ("", None):
            val = stored[sv.name]
        elif sv.default:
            val = sv.default
        else:
            if sv.required:
                missing.append(sv.name)
            continue

        if sv.type == "int":
            try:
                val = int(val)
            except (ValueError, TypeError):
                pass
        answers[sv.name] = val

    return answers, missing


def _resolve_survey_answers(schedule, template) -> tuple[dict, list[str]]:
    """Merge schedule-stored survey answers with template defaults.

    Priority (highest first):
    1. Values stored on the schedule (set by the operator when creating/editing it)
    2. Template default values
    3. If a required var has neither → added to the `missing` list

    Returns (answers_dict, missing_required_names).
    """
    stored: dict = {}
    try:
        stored = json.loads(schedule.survey_answers or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    answers: dict = {}
    missing: list[str] = []

    for sv in template.survey_vars:
        if sv.name in stored and stored[sv.name] not in ("", None):
            val = stored[sv.name]
        elif sv.default:
            val = sv.default
        else:
            if sv.required:
                missing.append(sv.name)
            continue

        # Cast to int where declared
        if sv.type == "int":
            try:
                val = int(val)
            except (ValueError, TypeError):
                pass
        answers[sv.name] = val

    return answers, missing


@celery.task(name="check_schedules")
def check_schedules() -> None:
    """Run once per minute (via Celery Beat). Checks all active schedules."""
    from app.tasks.run_task import _ensure_mongo
    _ensure_mongo()

    from app.models.schedule import Schedule
    from app.services.task_service import create_task, enqueue_task
    from croniter import croniter

    now = datetime.datetime.utcnow()

    for schedule in Schedule.objects(active=True):
        try:
            cron = croniter(schedule.cron_format, now - datetime.timedelta(minutes=1))
            next_run = cron.get_next(datetime.datetime)
            # Due if next_run falls within this minute window
            if not (now - datetime.timedelta(seconds=30) <= next_run <= now + datetime.timedelta(seconds=30)):
                continue

            if schedule.workflow:
                # ── Workflow schedule ─────────────────────────────────
                workflow = schedule.workflow
                survey_answers, missing = _resolve_survey_answers_from_vars(
                    schedule, workflow.survey_vars
                )
                if missing:
                    log.error(
                        "Schedule %s skipped: workflow '%s' has required survey vars "
                        "with no default: %s.",
                        schedule.id, workflow.name, ", ".join(missing),
                    )
                    continue

                from app.models.workflow_run import WorkflowRun
                from app.tasks.run_workflow import start_workflow as start_wf_task

                run = WorkflowRun(
                    project=schedule.project,
                    workflow=workflow,
                    status="waiting",
                    user=None,
                    survey_answers=json.dumps(survey_answers),
                ).save()
                start_wf_task.delay(str(run.id))
                log.info(
                    "Schedule %s → workflow run %s queued for '%s'",
                    schedule.id, run.id, workflow.name,
                )

            elif schedule.template:
                # ── Template schedule ─────────────────────────────────
                template = schedule.template
                survey_answers, missing = _resolve_survey_answers(schedule, template)
                if missing:
                    log.error(
                        "Schedule %s skipped: template '%s' has required survey vars "
                        "with no default: %s. Set defaults on the template to allow "
                        "scheduled execution.",
                        schedule.id, template.name, ", ".join(missing),
                    )
                    continue

                task = create_task(
                    template=template,
                    user=None,
                    survey_answers=survey_answers if survey_answers else None,
                    triggered_by="schedule",
                    trigger_name=schedule.cron_format,
                )
                enqueue_task(task)
                log.info("Schedule %s → task %s queued for template '%s'",
                         schedule.id, task.id, template.name)

            else:
                log.warning("Schedule %s has neither template nor workflow, skipping", schedule.id)

        except Exception as exc:
            log.error("Schedule %s error: %s", schedule.id, exc)

    # ── Commit-watch: autorun templates ───────────────────────────────────
    _check_autorun_templates(now)


def _remote_head(repo) -> str | None:
    """Get remote HEAD commit hash via git ls-remote (no full clone needed)."""
    import os
    import subprocess

    url    = repo.git_url
    branch = repo.git_branch or "main"

    env = {
        "PATH":                os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME":                os.environ.get("HOME", "/root"),
        "GIT_TERMINAL_PROMPT": "0",
    }

    key_path = None
    try:
        if repo.ssh_key and repo.ssh_key.type == "ssh":
            from app.services.crypto import decrypt
            import json as _json
            secret = _json.loads(decrypt(repo.ssh_key.secret) or "{}")
            pk = secret.get("private_key", "")
            if pk:
                from app.services.git_service import _key_file
                key_path = _key_file(pk, secret.get("passphrase", ""))
                env["GIT_SSH_COMMAND"] = (
                    f"ssh -i {key_path} -o StrictHostKeyChecking=no "
                    f"-o IdentitiesOnly=yes -o BatchMode=yes"
                )

        result = subprocess.run(
            ["git", "ls-remote", "--heads", url, f"refs/heads/{branch}"],
            capture_output=True, text=True, env=env, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.split()[0]
    except Exception as exc:
        log.debug("git ls-remote failed for %s: %s", url, exc)
    finally:
        if key_path:
            import os as _os
            try:
                _os.unlink(key_path)
            except OSError:
                pass
    return None


def _check_autorun_templates(now: datetime.datetime) -> None:
    """Trigger tasks for templates with autorun=True when a new commit is detected."""
    from app.models.template import Template
    from app.models.task import Task
    from app.services.task_service import create_task, enqueue_task

    for tmpl in Template.objects(autorun=True):
        if not tmpl.repository:
            continue
        try:
            remote_hash = _remote_head(tmpl.repository)
            if not remote_hash:
                continue

            # Find the commit hash of the last task for this template
            last_task = Task.objects(template=tmpl).order_by("-created_at").first()
            last_hash = last_task.commit_hash if last_task else None

            if last_hash == remote_hash:
                continue   # no new commit

            log.info(
                "Autorun: new commit %s detected for template '%s' (was %s)",
                remote_hash[:8], tmpl.name, (last_hash or "none")[:8],
            )
            task = create_task(
                template=tmpl,
                user=None,
                triggered_by="schedule",
                trigger_name=f"autorun:{remote_hash[:8]}",
            )
            enqueue_task(task)

        except Exception as exc:
            log.error("Autorun check failed for template %s: %s", tmpl.id, exc)
