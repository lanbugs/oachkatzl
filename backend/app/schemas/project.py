from apiflask.fields import Boolean, Integer, List, Nested, String
from apiflask.schemas import Schema
from marshmallow import validate

ROLES = ("owner", "manager", "task_runner", "guest")


class ProjectIn(Schema):
    name = String(required=True, validate=validate.Length(min=1, max=255))
    alert = Boolean(load_default=True)
    max_parallel_tasks = Integer(load_default=0)


class ProjectOut(Schema):
    id = String()
    name = String()
    alert = Boolean()
    max_parallel_tasks = Integer()
    created_at = String()
    demo = Boolean()


class MemberIn(Schema):
    user_id = String(required=True)
    role = String(required=True, validate=validate.OneOf(ROLES))


class MemberOut(Schema):
    id = String()
    user_id = String()
    username = String()
    email = String()
    role = String()
