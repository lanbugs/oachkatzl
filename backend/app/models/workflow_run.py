from __future__ import annotations

import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    ReferenceField,
    StringField,
    DENY,
    NULLIFY,
)

from app.models.project import Project
from app.models.user import User

WORKFLOW_RUN_STATUSES = ("waiting", "running", "success", "error", "stopped")
WORKFLOW_NODE_RUN_STATUSES = ("pending", "running", "success", "error", "skipped", "stopped")


class WorkflowNodeRun(EmbeddedDocument):
    """Tracks the execution state of a single node within a workflow run."""

    node_id = StringField(required=True)
    task_id = StringField(default="")         # Task document id as string
    status = StringField(default="pending", choices=WORKFLOW_NODE_RUN_STATUSES)
    edges_fired = BooleanField(default=False)  # True after we have activated successor nodes


class WorkflowRun(Document):
    meta = {
        "collection": "workflow_runs",
        "indexes": ["project", "workflow", "-created_at"],
    }

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    workflow = ReferenceField("app.models.workflow.WorkflowTemplate", required=True, reverse_delete_rule=DENY)
    status = StringField(choices=WORKFLOW_RUN_STATUSES, default="waiting")
    node_runs = EmbeddedDocumentListField(WorkflowNodeRun)
    user = ReferenceField(User, null=True, reverse_delete_rule=NULLIFY)
    survey_answers = StringField(default="{}")   # JSON string
    artifact_run = ReferenceField("app.models.artifact.ArtifactRun", null=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    start = DateTimeField()
    end = DateTimeField()
