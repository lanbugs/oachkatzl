from __future__ import annotations

from mongoengine import BooleanField, Document, ReferenceField, StringField, NULLIFY

BUILTIN_APP_TYPES = frozenset({"ansible", "bash", "python"})


class CustomApp(Document):
    """Admin-defined executable that appears as an additional app type."""

    meta = {"collection": "custom_apps", "indexes": ["slug"]}

    slug = StringField(required=True, unique=True, max_length=64)
    title = StringField(required=True, max_length=255)
    icon = StringField(default="terminal")
    executable = StringField(required=True)  # binary name or path on worker
    default_args = StringField(default="[]")  # JSON array
    # Template string describing how to build arg list.
    # Placeholders: {file} {arguments} {survey_vars_json}
    args_template = StringField(default="{file} {arguments}")
    active = BooleanField(default=True)
    worker_pool = ReferenceField("app.models.worker_pool.WorkerPool", null=True, reverse_delete_rule=NULLIFY)
