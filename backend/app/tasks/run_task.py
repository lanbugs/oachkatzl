from __future__ import annotations

import datetime
import logging
import os

log = logging.getLogger(__name__)

import redis as redis_lib

from app.celery_app import celery
from app.config import settings

# Use python-socketio's RedisManager in write_only mode — the documented pattern
# for publishing SocketIO events from background workers (Celery, etc.).
# The API server's flask-socketio with the same Redis message_queue receives these
# and delivers them to subscribed clients.
_mgr = None

LOG_FLUSH_EVERY = 5    # flush to MongoDB every N lines so polling sees progress


def _get_mgr():
    global _mgr
    if _mgr is None:
        import socketio as _sio
        _mgr = _sio.RedisManager(settings.REDIS_URL, write_only=True)
    return _mgr


def _emit(event: str, data: dict, task_id: str) -> None:
    try:
        _get_mgr().emit(event, data, room=f"task:{task_id}", namespace="/")
    except Exception:
        pass


def _should_stop(r: redis_lib.Redis, task_id: str) -> bool:
    return bool(r.get(f"stop:{task_id}"))


def _flush_log(task, log_lines: list[str]) -> None:
    """Write current log lines to MongoDB so polling can pick them up."""
    from app.models.task import TaskLog
    try:
        output = "\n".join(log_lines)
        existing = TaskLog.objects(task=task).first()
        if existing:
            existing.output = output
            existing.save()
        else:
            TaskLog(task=task, output=output).save()
    except Exception:
        pass


def _inject_artifact_token(task, env: dict, r) -> None:
    """Inject artifact token and URL pairs into the task environment.

    For workflow tasks the token is parked in Redis by start_workflow.
    For standalone tasks we create the ArtifactRun here if the template has a cache.
    """
    try:
        art_run = task.artifact_run
        if art_run:
            # Workflow path: raw token stored in Redis with TTL
            raw = r.get(f"artifact_token:{art_run.id}")
            if raw:
                _set_artifact_env(env, raw.decode())
            return

        # Standalone task path: create ArtifactRun if template has cache
        template = task.template
        cache = None
        try:
            cache = template.artifact_cache
        except Exception:
            pass

        if not cache:
            return

        from app.services.artifact_service import create_artifact_run
        art_run, raw_token = create_artifact_run(cache=cache, task=task)
        task.artifact_run = art_run
        task.save()
        _set_artifact_env(env, raw_token)
    except Exception as exc:
        log.warning("Artifact token injection failed: %s", exc)


def _set_artifact_env(env: dict, token: str) -> None:
    """Write all six artifact env vars into env."""
    internal = settings.INTERNAL_API_URL.rstrip("/")
    external = settings.BASE_URL.rstrip("/")
    env["OACHKATZL_ARTIFACT_TOKEN"]        = token
    env["OACHKATZL_ARTIFACT_URL"]          = internal + "/api/artifacts/upload"
    env["OACHKATZL_ARTIFACT_LIST_URL"]     = internal + "/api/artifacts/list"
    env["OACHKATZL_ARTIFACT_URL_EXT"]      = external + "/api/artifacts/upload"
    env["OACHKATZL_ARTIFACT_LIST_URL_EXT"] = external + "/api/artifacts/list"


def _ensure_mongo() -> None:
    """Connect to MongoDB if not already connected (safe in forked workers and tests)."""
    import mongoengine
    from mongoengine.connection import get_connection

    try:
        get_connection().server_info()   # raises if connection is gone
    except Exception:
        mongoengine.disconnect_all()
        mongoengine.connect(host=settings.MONGO_URI)


@celery.task(bind=True, name="run_task")
def run_task(self, task_id: str) -> None:
    _ensure_mongo()

    from app.models.task import Task, TaskLog
    from app.models.custom_app import CustomApp

    r = redis_lib.from_url(settings.REDIS_URL)

    try:
        task = Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return

    if task.status not in ("waiting", "starting"):
        return

    log_lines: list[str] = []
    flush_counter = 0

    def on_line(line: str) -> None:
        nonlocal flush_counter
        log_lines.append(line)
        _emit("task_output", {"task_id": task_id, "line": line}, task_id)
        flush_counter += 1
        if flush_counter >= LOG_FLUSH_EVERY:
            flush_counter = 0
            _flush_log(task, log_lines)

    task.status = "running"
    task.start = datetime.datetime.utcnow()
    task.save()
    _emit("task_status", {"task_id": task_id, "status": "running"}, task_id)
    on_line(f"[oachkatzl] Task {task_id} started")

    template = task.template
    workdir = os.path.join(settings.GIT_WORKDIR, task_id)
    cleanup_files: list[str] = []
    exit_code = 1

    try:
        if template.repository:
            from app.services.git_service import clone_or_update
            commit_hash = clone_or_update(
                template.repository, workdir,
                debug=task.debug, on_line=on_line,
                pin_commit=task.pin_commit or "",
            )
            task.commit_hash = commit_hash
            task.save()
            on_line(f"[oachkatzl] Repo ready at {commit_hash[:8]}")
        else:
            os.makedirs(workdir, exist_ok=True)

        from app.tasks.executor import build_env
        env, _ = build_env(task, workdir)

        # Inject artifact cache token when template or workflow has a cache configured
        _inject_artifact_token(task, env, r)

        from app.tasks.apply_credentials import apply_credentials
        cred_env, cred_extra_vars, cred_cleanup = apply_credentials(task)
        env.update(cred_env)
        cleanup_files.extend(cred_cleanup)

        app_type = template.app
        if app_type == "ansible":
            from app.tasks.apps.ansible_app import build_command, galaxy_install

            # Set isolated Galaxy paths so concurrent tasks don't collide
            galaxy_roles_path       = os.path.join(workdir, ".galaxy", "roles")
            galaxy_collections_path = os.path.join(workdir, ".galaxy", "collections")
            env["ANSIBLE_ROLES_PATH"] = (
                galaxy_roles_path + ":" + env.get("ANSIBLE_ROLES_PATH", "")
            ).rstrip(":")
            env["ANSIBLE_COLLECTIONS_PATHS"] = (
                galaxy_collections_path + ":" + env.get("ANSIBLE_COLLECTIONS_PATHS", "")
            ).rstrip(":")

            galaxy_install(workdir, env, on_line, debug=task.debug)
            cmd, cleanup_files = build_command(task, workdir, cred_extra_vars=cred_extra_vars)
        elif app_type == "bash":
            from app.tasks.apps.bash_app import build_command
            cmd, cleanup_files = build_command(task, workdir)
        elif app_type == "python":
            from app.tasks.apps.python_app import build_command, venv_install
            python_exe = venv_install(workdir, env, on_line, debug=task.debug)
            # Add venv bin to PATH so sub-processes also see installed packages
            venv_bin = os.path.join(workdir, ".venv", "bin")
            if os.path.isdir(venv_bin):
                env["PATH"] = venv_bin + ":" + env.get("PATH", "")
                env["VIRTUAL_ENV"] = os.path.join(workdir, ".venv")
            cmd, cleanup_files = build_command(task, workdir, python_executable=python_exe)
        else:
            try:
                custom_app = CustomApp.objects.get(slug=app_type, active=True)
                from app.tasks.apps.custom_app import build_command
                cmd, cleanup_files = build_command(task, workdir, custom_app)
            except CustomApp.DoesNotExist:
                raise ValueError(f"Unknown app type: {app_type}")

        from app.tasks.executor import run_command

        exit_code = run_command(
            cmd,
            env,
            workdir,
            on_line=on_line,
            stop_flag=lambda: _should_stop(r, task_id),
        )

    except Exception as exc:
        log.error("Task %s failed: %s", task_id, exc, exc_info=True)
        on_line("[oachkatzl] ERROR: task execution failed — check server logs for details")
        exit_code = 1
    finally:
        for f in cleanup_files:
            try:
                os.unlink(f)
            except OSError:
                pass

        from app.services.git_service import cleanup_workdir
        cleanup_workdir(workdir)

        if _should_stop(r, task_id):
            task.status = "stopped"
            r.delete(f"stop:{task_id}")
        elif exit_code == 0:
            task.status = "success"
        else:
            task.status = "error"

        task.exit_code = exit_code
        task.end = datetime.datetime.utcnow()
        task.save()

        on_line(f"[oachkatzl] Task finished — status={task.status} exit_code={exit_code}")
        _flush_log(task, log_lines)   # final flush
        _emit("task_status", {"task_id": task_id, "status": task.status}, task_id)

        # Workflow-triggered tasks skip per-task notifications; the workflow run
        # fires its own notification when all nodes are done.
        if task.triggered_by != "workflow":
            try:
                template_suppress = task.template.suppress_success_alerts
                if not (task.status == "success" and template_suppress):
                    from app.services.notify_service import notify_task_result
                    notify_task_result(task)
            except Exception as exc:
                log.error("Notification dispatch error: %s", exc)
