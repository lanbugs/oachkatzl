from __future__ import annotations

import datetime

from mongoengine import DateTimeField, Document, ReferenceField, StringField, DENY, NULLIFY

from app.models.project import Project
from app.models.access_key import AccessKey


class Repository(Document):
    meta = {"collection": "repositories", "indexes": ["project"]}

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    name = StringField(required=True, max_length=255)
    git_url = StringField(required=True)
    git_branch = StringField(default="main")
    ssh_key = ReferenceField(AccessKey, null=True, reverse_delete_rule=NULLIFY)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
