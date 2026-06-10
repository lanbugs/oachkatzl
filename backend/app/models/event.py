from __future__ import annotations

import datetime

from mongoengine import DateTimeField, Document, ReferenceField, StringField, NULLIFY

from app.models.project import Project
from app.models.user import User


class Event(Document):
    meta = {
        "collection": "events",
        "indexes": ["-created_at", "project"],
    }

    project = ReferenceField(Project, null=True, reverse_delete_rule=NULLIFY)
    user = ReferenceField(User, null=True, reverse_delete_rule=NULLIFY)
    object_type = StringField(default="")
    object_id = StringField(default="")
    action = StringField(required=True)
    description = StringField(default="")
    created_at = DateTimeField(default=datetime.datetime.utcnow)
