from __future__ import annotations

from mongoengine import Document, IntField, ReferenceField, StringField, DENY

from app.models.project import Project


class View(Document):
    meta = {"collection": "views", "indexes": ["project"]}

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    title = StringField(required=True, max_length=255)
    position = IntField(default=0)
