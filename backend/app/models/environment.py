from __future__ import annotations

import datetime

from mongoengine import (
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    ReferenceField,
    StringField,
    DENY,
)

from app.models.project import Project


class EnvironmentSecret(EmbeddedDocument):
    """Encrypted environment secret (name=plaintext, value=Fernet-encrypted)."""

    name = StringField(required=True)
    value = StringField(default="")  # Fernet-encrypted


class Environment(Document):
    meta = {"collection": "environments", "indexes": ["project"]}

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    name = StringField(required=True, max_length=255)
    json = StringField(default="{}")   # extra_vars as JSON string
    env = StringField(default="{}")    # env vars as JSON string
    secrets = EmbeddedDocumentListField(EnvironmentSecret)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
