from __future__ import annotations

import datetime

from mongoengine import (
    DateTimeField,
    Document,
    FileField,
    IntField,
    LongField,
    ReferenceField,
    StringField,
    DENY,
)

from app.models.project import Project


class ArtifactCache(Document):
    """Project-level named cache configuration (stores no data itself)."""

    meta = {"collection": "artifact_caches", "indexes": ["project"]}

    project        = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    name           = StringField(required=True, max_length=255)
    description    = StringField(default="")
    retention_days = IntField(default=30)   # 0 = no expiry
    created_at     = DateTimeField(default=datetime.datetime.utcnow)


class ArtifactRun(Document):
    """Token scope for one task run or workflow run. All artifacts belong here."""

    meta = {
        "collection": "artifact_runs",
        "indexes": ["cache", "task", "workflow_run", "token_hash"],
    }

    cache        = ReferenceField(ArtifactCache, required=True, reverse_delete_rule=DENY)
    token_hash   = StringField(required=True, unique=True)   # SHA-256 hex, raw token never stored
    task         = ReferenceField("app.models.task.Task", null=True)
    workflow_run = ReferenceField("app.models.workflow_run.WorkflowRun", null=True)
    expires_at   = DateTimeField(null=True)   # None = no expiry
    created_at   = DateTimeField(default=datetime.datetime.utcnow)


class Artifact(Document):
    """A single artifact (file or JSON) within an ArtifactRun."""

    meta = {"collection": "artifacts", "indexes": ["run", "-created_at"]}

    run           = ReferenceField(ArtifactRun, required=True, reverse_delete_rule=DENY)
    name          = StringField(required=True, max_length=512)
    artifact_type = StringField(choices=("file", "json"), required=True)
    content_type  = StringField(default="application/octet-stream")
    json_data     = StringField(default="")   # serialised JSON string for artifact_type=json
    file_data     = FileField(null=True)       # GridFS for artifact_type=file
    size_bytes    = LongField(default=0)
    created_at    = DateTimeField(default=datetime.datetime.utcnow)
