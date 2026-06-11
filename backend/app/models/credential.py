from __future__ import annotations

import datetime

from mongoengine import DateTimeField, Document, ReferenceField, StringField, DENY

from app.models.project import Project
from app.models.credential_type import CredentialType


class Credential(Document):
    meta = {"collection": "credentials", "indexes": ["project"]}

    project         = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    name            = StringField(required=True, max_length=255)
    credential_type = ReferenceField(CredentialType, required=True, reverse_delete_rule=DENY)
    # Fernet-encrypted JSON: {field_id: plaintext_value}
    inputs          = StringField(default="")
    created_at      = DateTimeField(default=datetime.datetime.utcnow)
