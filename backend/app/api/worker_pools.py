from __future__ import annotations

import re

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Boolean, String
from apiflask.schemas import Schema

from app.services.rbac import require_admin, require_auth

bp = APIBlueprint("worker_pools", __name__, url_prefix="/api/worker-pools")

_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9_-]*$')


class WorkerPoolIn(Schema):
    slug = String(required=True)
    name = String(required=True)
    description = String(load_default="")
    active = Boolean(load_default=True)


class WorkerPoolOut(Schema):
    id = String()
    slug = String()
    name = String()
    description = String()
    active = Boolean()
    created_at = String()


def _out(wp) -> dict:
    return {
        "id": str(wp.id),
        "slug": wp.slug,
        "name": wp.name,
        "description": wp.description,
        "active": wp.active,
        "created_at": wp.created_at.isoformat() if wp.created_at else None,
    }


@bp.get("/")
@require_auth
@bp.output(WorkerPoolOut(many=True))
def list_worker_pools():
    from app.models.worker_pool import WorkerPool
    return [_out(wp) for wp in WorkerPool.objects().order_by("name")]


@bp.post("/")
@require_admin
@bp.input(WorkerPoolIn, arg_name="body")
@bp.output(WorkerPoolOut, status_code=201)
def create_worker_pool(body):
    from app.models.worker_pool import WorkerPool
    if not _SLUG_RE.match(body["slug"]):
        raise HTTPError(400, "Slug must match [a-z0-9][a-z0-9_-]*")
    if body["slug"] == "celery":
        raise HTTPError(400, "'celery' is the reserved default queue name")
    if WorkerPool.objects(slug=body["slug"]).first():
        raise HTTPError(409, "Slug already exists")
    wp = WorkerPool(**body).save()
    return _out(wp)


@bp.get("/<pool_id>")
@require_auth
@bp.output(WorkerPoolOut)
def get_worker_pool(pool_id):
    from app.models.worker_pool import WorkerPool
    try:
        return _out(WorkerPool.objects.get(id=pool_id))
    except WorkerPool.DoesNotExist:
        raise HTTPError(404, "Worker pool not found")


@bp.put("/<pool_id>")
@require_admin
@bp.input(WorkerPoolIn, arg_name="body")
@bp.output(WorkerPoolOut)
def update_worker_pool(pool_id, body):
    from app.models.worker_pool import WorkerPool
    try:
        wp = WorkerPool.objects.get(id=pool_id)
    except WorkerPool.DoesNotExist:
        raise HTTPError(404, "Worker pool not found")
    # slug is immutable after creation
    for k in ("name", "description", "active"):
        if k in body:
            setattr(wp, k, body[k])
    wp.save()
    return _out(wp)


@bp.delete("/<pool_id>")
@require_admin
def delete_worker_pool(pool_id):
    from app.models.worker_pool import WorkerPool
    from app.models.template import Template
    from app.models.custom_app import CustomApp
    try:
        wp = WorkerPool.objects.get(id=pool_id)
    except WorkerPool.DoesNotExist:
        raise HTTPError(404, "Worker pool not found")
    if Template.objects(worker_pool=wp).first():
        raise HTTPError(409, "Worker pool is referenced by one or more templates")
    if CustomApp.objects(worker_pool=wp).first():
        raise HTTPError(409, "Worker pool is referenced by one or more custom apps")
    wp.delete()
    return {"message": "Deleted"}, 200
