from __future__ import annotations

import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    ReferenceField,
    StringField,
    DENY,
    NULLIFY,
)

from app.models.project import Project
from app.models.template import Template
from app.models.repository import Repository


class Schedule(Document):
    meta = {"collection": "schedules", "indexes": ["project", "active"]}

    project  = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    # Exactly one of template / workflow must be set.
    template = ReferenceField(Template, null=True, reverse_delete_rule=DENY)
    workflow = ReferenceField(
        "app.models.workflow.WorkflowTemplate", null=True, reverse_delete_rule=DENY
    )
    cron_format = StringField(required=True)
    active = BooleanField(default=True)
    last_commit_hash = StringField(default="")
    repository = ReferenceField(Repository, null=True, reverse_delete_rule=NULLIFY)
    # Pre-configured survey answers (JSON dict). Used instead of resource
    # defaults when the schedule fires so no user interaction is needed.
    survey_answers = StringField(default="{}")
    created_at = DateTimeField(default=datetime.datetime.utcnow)
