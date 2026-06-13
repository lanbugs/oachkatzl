from __future__ import annotations

import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    ListField,
    ReferenceField,
    StringField,
    DENY,
    NULLIFY,
    PULL,
)

from app.models.project import Project
from app.models.repository import Repository
from app.models.inventory import Inventory
from app.models.environment import Environment
from app.models.view import View
from app.models.access_key import AccessKey
from app.models.credential import Credential

APP_TYPES = ("ansible", "bash", "python")   # + custom app slugs validated in service
TEMPLATE_TYPES = ("task", "build", "deploy")
SURVEY_VAR_TYPES = ("string", "int", "enum", "secret", "bool", "separator")


class SurveyVar(EmbeddedDocument):
    name = StringField(required=True)
    title = StringField(default="")
    description = StringField(default="")
    type = StringField(choices=SURVEY_VAR_TYPES, default="string")
    required = BooleanField(default=False)
    default = StringField(default="")
    values = ListField(StringField())   # for enum type


class VaultRef(EmbeddedDocument):
    """Reference to an AccessKey of type 'vault'."""

    vault_id = StringField(required=True)   # logical ID within template
    name = StringField(default="")
    key = ReferenceField(AccessKey)   # no reverse_delete_rule in EmbeddedDocuments


class Template(Document):
    meta = {"collection": "templates", "indexes": ["project"]}

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    name = StringField(required=True, max_length=255)
    description = StringField(default="")
    app = StringField(required=True)   # ansible / bash / python / custom-slug
    type = StringField(choices=TEMPLATE_TYPES, default="task")
    playbook = StringField(default="")   # relative path in repo
    repository = ReferenceField(Repository, null=True, reverse_delete_rule=NULLIFY)
    inventory = ReferenceField(Inventory, null=True, reverse_delete_rule=NULLIFY)
    environment = ReferenceField(Environment, null=True, reverse_delete_rule=NULLIFY)
    arguments = StringField(default="[]")   # JSON array
    allow_override_args = BooleanField(default=False)
    allow_parallel = BooleanField(default=False)
    suppress_success_alerts = BooleanField(default=False)
    view = ReferenceField(View, null=True, reverse_delete_rule=NULLIFY)
    vaults = EmbeddedDocumentListField(VaultRef)
    survey_vars = EmbeddedDocumentListField(SurveyVar)
    build_template = ReferenceField("self", null=True, reverse_delete_rule=NULLIFY)
    start_version  = StringField(default="")   # e.g. "1.0.0" — for type=build only
    autorun = BooleanField(default=False)
    credentials = ListField(ReferenceField(Credential, reverse_delete_rule=PULL))
    artifact_cache = ReferenceField("app.models.artifact.ArtifactCache", null=True)
    worker_pool = ReferenceField("app.models.worker_pool.WorkerPool", null=True, reverse_delete_rule=NULLIFY)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
