from apiflask.fields import Boolean, Dict, Float, List, Nested, String
from apiflask.schemas import Schema
from marshmallow import validate

from app.schemas.template import SurveyVarIn, SurveyVarOut


ACTION_NODE_TYPES = {"list_generator", "pdf_generator", "send_mail", "transfer_file"}


class WorkflowNodeIn(Schema):
    node_id = String(required=True)
    node_type = String(load_default="task")
    slug = String(load_default="")
    label = String(load_default="")
    template_id = String(load_default=None)
    action_config = Dict(load_default={})
    on_success = List(String(), load_default=[])
    on_failure = List(String(), load_default=[])
    on_always = List(String(), load_default=[])
    position_x = Float(load_default=0.0)
    position_y = Float(load_default=0.0)


class WorkflowNodeOut(Schema):
    node_id = String()
    node_type = String(dump_default="task")
    slug = String(dump_default="")
    label = String()
    template_id = String(dump_default=None)
    template_name = String(dump_default="")
    action_config = Dict(dump_default={})
    on_success = List(String())
    on_failure = List(String())
    on_always = List(String())
    position_x = Float(dump_default=0.0)
    position_y = Float(dump_default=0.0)


class WorkflowTemplateIn(Schema):
    name = String(required=True, validate=validate.Length(min=1, max=255))
    description = String(load_default="")
    nodes = List(Nested(WorkflowNodeIn), load_default=[])
    survey_vars = List(Nested(SurveyVarIn), load_default=[])
    allow_parallel = Boolean(load_default=False)
    suppress_success_alerts = Boolean(load_default=False)
    artifact_cache_id = String(load_default=None)


class WorkflowTemplateOut(Schema):
    id = String()
    project_id = String()
    name = String()
    description = String()
    nodes = List(Nested(WorkflowNodeOut))
    survey_vars = List(Nested(SurveyVarOut))
    allow_parallel = Boolean()
    suppress_success_alerts = Boolean()
    artifact_cache_id = String(dump_default=None)
    created_at = String()


class WorkflowNodeRunOut(Schema):
    node_id = String()
    node_type = String(dump_default="task")
    task_id = String(dump_default="")
    status = String()
    edges_fired = Boolean()
    template_name = String(dump_default="")
    label = String(dump_default="")


class WorkflowRunOut(Schema):
    id = String()
    workflow_id = String()
    workflow_name = String(dump_default="")
    project_id = String()
    status = String()
    node_runs = List(Nested(WorkflowNodeRunOut))
    user_id = String(dump_default=None)
    username = String(dump_default=None)
    survey_answers = String(dump_default="{}")
    pending_approval_node_id = String(dump_default="")
    created_at = String(dump_default=None)
    start = String(dump_default=None)
    end = String(dump_default=None)


class WorkflowStartIn(Schema):
    survey_answers = String(load_default="{}")
