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
from app.models.template import Template

AUTH_METHODS = ("none", "hmac", "token")
MATCH_TYPES = ("body", "header")
MATCH_METHODS = ("equals", "unequals", "contains", "exists")
VALUE_SOURCES = ("body", "header")


class IntegrationMatcher(EmbeddedDocument):
    match_type = StringField(choices=MATCH_TYPES, default="body")
    key = StringField(required=True)
    method = StringField(choices=MATCH_METHODS, default="equals")
    value = StringField(default="")


class IntegrationExtractValue(EmbeddedDocument):
    value_source = StringField(choices=VALUE_SOURCES, default="body")
    key = StringField(required=True)
    variable = StringField(required=True)
    variable_type = StringField(default="string")


class Integration(Document):
    meta = {"collection": "integrations", "indexes": ["project"]}

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    template = ReferenceField(Template, required=True, reverse_delete_rule=DENY)
    name = StringField(required=True, max_length=255)
    auth_method = StringField(choices=AUTH_METHODS, default="none")
    auth_secret = StringField(default="")   # Fernet-encrypted
    auth_header = StringField(default="")
    matchers = EmbeddedDocumentListField(IntegrationMatcher)
    extract_values = EmbeddedDocumentListField(IntegrationExtractValue)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
