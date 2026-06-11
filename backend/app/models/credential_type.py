from __future__ import annotations

import datetime

from mongoengine import DateTimeField, Document, StringField


class CredentialType(Document):
    meta = {"collection": "credential_types"}

    name        = StringField(required=True, max_length=255)
    description = StringField(default="")
    # JSON array: [{id, label, type, required, default, help_text}]
    inputs      = StringField(default="[]")
    # JSON object: {env: {VAR: "{{ field }}"}, extra_vars: {...}, file: {content: "{{ field }}", var: "PATH_VAR"}}
    injectors   = StringField(default="{}")
    created_at  = DateTimeField(default=datetime.datetime.utcnow)
