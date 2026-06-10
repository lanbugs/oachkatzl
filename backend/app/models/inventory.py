from __future__ import annotations

import datetime

from mongoengine import DateTimeField, Document, ReferenceField, StringField, DENY, NULLIFY

from app.models.project import Project
from app.models.access_key import AccessKey

INVENTORY_TYPES = ("static", "static-yaml", "file", "none")


class Inventory(Document):
    meta = {"collection": "inventories", "indexes": ["project"]}

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    name = StringField(required=True, max_length=255)
    type = StringField(required=True, choices=INVENTORY_TYPES, default="none")
    inventory = StringField(default="")          # INI/YAML text for static types
    inventory_file = StringField(default="")     # repo-relative path for file type
    ssh_key = ReferenceField(AccessKey, null=True, reverse_delete_rule=NULLIFY)
    become_key = ReferenceField(AccessKey, null=True, reverse_delete_rule=NULLIFY)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
