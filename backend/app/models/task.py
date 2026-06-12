from __future__ import annotations

import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    IntField,
    ReferenceField,
    StringField,
    DENY,
    NULLIFY,
)

from app.models.project import Project
from app.models.template import Template
from app.models.user import User
from app.models.runner import Runner

TASK_STATUSES = ("waiting", "starting", "running", "success", "error", "stopped")


class Task(Document):
    meta = {
        "collection": "tasks",
        "indexes": ["project", "template", "-created_at"],
    }

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    template = ReferenceField(Template, required=True, reverse_delete_rule=DENY)
    status = StringField(choices=TASK_STATUSES, default="waiting")
    debug = BooleanField(default=False)
    dry_run = BooleanField(default=False)
    diff = BooleanField(default=False)
    user = ReferenceField(User, null=True, reverse_delete_rule=NULLIFY)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    start = DateTimeField()
    end = DateTimeField()
    message = StringField(default="")
    commit_hash = StringField(default="")
    commit_message = StringField(default="")
    version = StringField(default="")          # build version for type=build
    build_task = ReferenceField("self", null=True, reverse_delete_rule=NULLIFY)
    environment_override = StringField(default="{}")
    arguments_override = StringField(default="[]")
    survey_answers = StringField(default="{}")
    runner = ReferenceField(Runner, null=True, reverse_delete_rule=NULLIFY)
    exit_code = IntField()
    # How the task was triggered
    triggered_by = StringField(choices=("manual", "schedule", "token", "workflow"), default="manual")
    trigger_name = StringField(default="")   # token name / workflow_run_id
    # If set, the worker checks out this specific commit instead of HEAD
    pin_commit = StringField(default="")
    # Artifact run associated with this task (set when template has artifact_cache)
    artifact_run = ReferenceField("app.models.artifact.ArtifactRun", null=True)


class TaskLog(Document):
    """Archived full log for a completed task."""

    meta = {"collection": "task_logs", "indexes": ["task"]}

    task = ReferenceField(Task, required=True, reverse_delete_rule=DENY)
    output = StringField(default="")
    created_at = DateTimeField(default=datetime.datetime.utcnow)
