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
)

from app.models.user import User

ROLES = ("owner", "manager", "task_runner", "guest")


class Project(Document):
    meta = {"collection": "projects", "indexes": ["name"]}

    name = StringField(required=True, max_length=255)
    alert = BooleanField(default=True)
    max_parallel_tasks = IntField(default=0)  # 0 = unlimited
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    demo = BooleanField(default=False)


class ProjectMember(Document):
    meta = {
        "collection": "project_members",
        "indexes": [{"fields": ("project", "user"), "unique": True}],
    }

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    user    = ReferenceField(User,    required=True, reverse_delete_rule=DENY)
    role    = StringField(required=True, choices=ROLES, default="guest")
    source  = StringField(choices=("manual", "ldap"), default="manual")
