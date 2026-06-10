from __future__ import annotations

import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    ReferenceField,
    StringField,
    DENY,
)

from app.models.project import Project
from app.models.template import Template


class TemplateToken(Document):
    """Token that allows triggering a specific template without full API auth.

    The raw token is shown once at creation time; only the SHA-256 hash is
    stored so the database never contains recoverable credentials.
    """

    meta = {"collection": "template_tokens", "indexes": ["template", "token_hash"]}

    template    = ReferenceField(Template, required=True, reverse_delete_rule=DENY)
    project     = ReferenceField(Project,  required=True, reverse_delete_rule=DENY)
    name        = StringField(required=True, max_length=255)
    token_hash  = StringField(required=True, unique=True)   # SHA-256 hex
    # Pre-configured survey answers (JSON). Values in the request body override these.
    survey_defaults = StringField(default="{}")
    created_at  = DateTimeField(default=datetime.datetime.utcnow)
    expires_at  = DateTimeField(null=True)
    active      = BooleanField(default=True)
