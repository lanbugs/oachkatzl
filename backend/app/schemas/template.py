from apiflask.fields import Boolean, List, Nested, String
from apiflask.schemas import Schema
from marshmallow import validate

TEMPLATE_TYPES = ("task", "build", "deploy")
SURVEY_TYPES = ("string", "int", "enum", "secret", "bool", "separator")


class SurveyVarIn(Schema):
    name = String(required=True)
    title = String(load_default="")
    description = String(load_default="")
    type = String(load_default="string", validate=validate.OneOf(SURVEY_TYPES))
    required = Boolean(load_default=False)
    default = String(load_default="")
    values = List(String(), load_default=[])


class SurveyVarOut(Schema):
    name = String()
    title = String()
    description = String()
    type = String()
    required = Boolean()
    default = String()
    values = List(String())


class VaultRefIn(Schema):
    vault_id = String(required=True)
    name = String(load_default="")
    key_id = String(load_default=None)


class VaultRefOut(Schema):
    vault_id = String()
    name = String()
    key_id = String(dump_default=None)


class TemplateIn(Schema):
    name = String(required=True, validate=validate.Length(min=1, max=255))
    description = String(load_default="")
    app = String(required=True)
    type = String(load_default="task", validate=validate.OneOf(TEMPLATE_TYPES))
    playbook = String(load_default="")
    repository_id = String(load_default=None)
    inventory_id = String(load_default=None)
    environment_id = String(load_default=None)
    arguments = String(load_default="[]")
    allow_override_args = Boolean(load_default=False)
    allow_parallel = Boolean(load_default=False)
    suppress_success_alerts = Boolean(load_default=False)
    view_id = String(load_default=None)
    survey_vars       = List(Nested(SurveyVarIn), load_default=[])
    vaults            = List(Nested(VaultRefIn), load_default=[])
    start_version     = String(load_default="")    # "x.y.z" — build type only
    build_template_id = String(load_default=None)  # deploy type: source build template
    autorun = Boolean(load_default=False)
    credential_ids     = List(String(), load_default=[])
    artifact_cache_id  = String(load_default=None)
    worker_pool_id     = String(load_default=None)


class TemplateOut(Schema):
    id = String()
    name = String()
    description = String()
    app = String()
    type = String()
    playbook = String()
    repository_id = String(dump_default=None)
    inventory_id = String(dump_default=None)
    environment_id = String(dump_default=None)
    arguments = String()
    allow_override_args = Boolean()
    allow_parallel = Boolean()
    suppress_success_alerts = Boolean()
    view_id = String(dump_default=None)
    survey_vars       = List(Nested(SurveyVarOut))
    vaults            = List(Nested(VaultRefOut))
    start_version     = String(dump_default="")
    build_template_id = String(dump_default=None)
    autorun            = Boolean(dump_default=False)
    credential_ids     = List(String(), dump_default=[])
    artifact_cache_id  = String(dump_default=None)
    worker_pool_id     = String(dump_default=None)
    worker_pool_name   = String(dump_default=None)
    created_at = String()
