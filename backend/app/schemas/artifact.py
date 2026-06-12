from apiflask.fields import Boolean, Integer, String
from apiflask.schemas import Schema
from marshmallow import validate


class ArtifactCacheIn(Schema):
    name           = String(required=True, validate=validate.Length(min=1, max=255))
    description    = String(load_default="")
    retention_days = Integer(load_default=30, validate=validate.Range(min=0))


class ArtifactCacheOut(Schema):
    id             = String()
    project_id     = String()
    name           = String()
    description    = String()
    retention_days = Integer()
    created_at     = String(dump_default=None)


class ArtifactRunOut(Schema):
    id              = String()
    cache_id        = String()
    cache_name      = String(dump_default="")
    task_id         = String(dump_default=None)
    workflow_run_id = String(dump_default=None)
    artifact_count  = Integer(dump_default=0)
    expires_at      = String(dump_default=None)
    created_at      = String(dump_default=None)


class ArtifactOut(Schema):
    id            = String()
    run_id        = String()
    name          = String()
    artifact_type = String()
    content_type  = String()
    size_bytes    = Integer()
    created_at    = String(dump_default=None)
