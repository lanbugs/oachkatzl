from __future__ import annotations

import datetime

from mongoengine import DateTimeField, Document, ReferenceField, StringField, DENY

from app.models.project import Project

KEY_TYPES = ("none", "ssh", "login_password", "vault")


class AccessKey(Document):
    meta = {"collection": "access_keys", "indexes": ["project"]}

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    name = StringField(required=True, max_length=255)
    type = StringField(required=True, choices=KEY_TYPES, default="none")
    # Fernet-encrypted JSON: {private_key, passphrase} / {login, password} / {vault_password}
    secret = StringField(default="")
    created_at = DateTimeField(default=datetime.datetime.utcnow)
