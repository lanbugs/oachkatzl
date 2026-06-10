from apiflask.fields import Boolean, Integer, String
from apiflask.schemas import Schema
from marshmallow import validate

TASK_STATUSES = ("waiting", "starting", "running", "success", "error", "stopped")


class TaskStartIn(Schema):
    debug = Boolean(load_default=False)
    dry_run = Boolean(load_default=False)
    diff = Boolean(load_default=False)
    environment_override = String(load_default="{}")
    arguments_override = String(load_default="[]")
    survey_answers = String(load_default="{}")
    build_task_id = String(load_default=None)   # deploy-type: which build to deploy


class TaskOut(Schema):
    id = String()
    template_id = String()
    status = String()
    debug = Boolean()
    dry_run = Boolean()
    diff = Boolean()
    user_id = String(dump_default=None)
    created_at = String()
    start = String(dump_default=None)
    end = String(dump_default=None)
    message = String()
    commit_hash = String()
    version = String()
    build_task_id = String(dump_default=None)
    exit_code = Integer(dump_default=None)
    triggered_by = String(dump_default="manual")
    trigger_name = String(dump_default="")


class TaskLogOut(Schema):
    task_id = String()
    output = String()
