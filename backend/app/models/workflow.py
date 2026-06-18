from __future__ import annotations

import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    DictField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    FloatField,
    ListField,
    ReferenceField,
    StringField,
    DENY,
)

from app.models.project import Project
from app.models.template import Template, SurveyVar


class WorkflowNode(EmbeddedDocument):
    """A single node in the workflow DAG."""

    node_id = StringField(required=True)       # uuid4 string, unique within workflow
    node_type = StringField(
        default="task",
        choices=("task", "question", "remote_approval", "list_generator", "pdf_generator", "send_mail", "transfer_file"),
    )
    action_config = DictField(default=dict)
    slug = StringField(default="")             # user-defined artifact key for question nodes
    label = StringField(default="")
    template = ReferenceField(Template)         # no reverse_delete_rule in EmbeddedDocument
    on_success = ListField(StringField())       # node_ids to activate when this node succeeds
    on_failure = ListField(StringField())       # node_ids to activate when this node fails/stops
    on_always = ListField(StringField())        # node_ids to always activate after this node
    position_x = FloatField(default=0.0)
    position_y = FloatField(default=0.0)


class WorkflowTemplate(Document):
    meta = {"collection": "workflow_templates", "indexes": ["project"]}

    project = ReferenceField(Project, required=True, reverse_delete_rule=DENY)
    name = StringField(required=True, max_length=255)
    description = StringField(default="")
    nodes = EmbeddedDocumentListField(WorkflowNode)
    survey_vars = EmbeddedDocumentListField(SurveyVar)
    allow_parallel = BooleanField(default=False)
    suppress_success_alerts = BooleanField(default=False)
    artifact_cache = ReferenceField("app.models.artifact.ArtifactCache", null=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
