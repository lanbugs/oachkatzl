from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Boolean, String
from apiflask.schemas import Schema
from flask import g

from app.services.rbac import require_admin, require_auth

bp = APIBlueprint("custom_apps", __name__, url_prefix="/api/custom-apps")


class CustomAppIn(Schema):
    slug = String(required=True)
    title = String(required=True)
    icon = String(load_default="terminal")
    executable = String(required=True)
    default_args = String(load_default="[]")
    args_template = String(load_default="{file} {arguments}")
    active = Boolean(load_default=True)
    worker_pool_id = String(load_default=None)


class CustomAppOut(Schema):
    id = String()
    slug = String()
    title = String()
    icon = String()
    executable = String()
    default_args = String()
    args_template = String()
    active = Boolean()
    worker_pool_id = String()
    worker_pool_name = String()


def _out(ca) -> dict:
    return {
        "id": str(ca.id),
        "slug": ca.slug,
        "title": ca.title,
        "icon": ca.icon,
        "executable": ca.executable,
        "default_args": ca.default_args,
        "args_template": ca.args_template,
        "active": ca.active,
        "worker_pool_id":   str(ca.worker_pool.id) if ca.worker_pool else None,
        "worker_pool_name": ca.worker_pool.name if ca.worker_pool else None,
    }


@bp.get("/")
@require_auth
@bp.output(CustomAppOut(many=True))
def list_custom_apps():
    from app.models.custom_app import CustomApp
    return [_out(ca) for ca in CustomApp.objects(active=True)]


def _resolve_worker_pool(pool_id: str | None):
    if not pool_id:
        return None
    from app.models.worker_pool import WorkerPool
    try:
        return WorkerPool.objects.get(id=pool_id)
    except WorkerPool.DoesNotExist:
        return None


@bp.post("/")
@require_admin
@bp.input(CustomAppIn, arg_name="body")
@bp.output(CustomAppOut, status_code=201)
def create_custom_app(body):
    from app.models.custom_app import CustomApp, BUILTIN_APP_TYPES
    if body["slug"] in BUILTIN_APP_TYPES:
        raise HTTPError(400, f"'{body['slug']}' is a reserved built-in app type")
    if CustomApp.objects(slug=body["slug"]).first():
        raise HTTPError(409, "Slug already exists")
    pool_id = body.pop("worker_pool_id", None)
    ca = CustomApp(**body, worker_pool=_resolve_worker_pool(pool_id)).save()
    return _out(ca)


@bp.get("/<app_id>")
@require_auth
@bp.output(CustomAppOut)
def get_custom_app(app_id):
    from app.models.custom_app import CustomApp
    try:
        return _out(CustomApp.objects.get(id=app_id))
    except CustomApp.DoesNotExist:
        raise HTTPError(404, "Custom app not found")


@bp.put("/<app_id>")
@require_admin
@bp.input(CustomAppIn, arg_name="body")
@bp.output(CustomAppOut)
def update_custom_app(app_id, body):
    from app.models.custom_app import CustomApp
    try:
        ca = CustomApp.objects.get(id=app_id)
    except CustomApp.DoesNotExist:
        raise HTTPError(404, "Custom app not found")
    pool_id = body.pop("worker_pool_id", None)
    for k, v in body.items():
        setattr(ca, k, v)
    ca.worker_pool = _resolve_worker_pool(pool_id)
    ca.save()
    return _out(ca)


@bp.delete("/<app_id>")
@require_admin
def delete_custom_app(app_id):
    from app.models.custom_app import CustomApp
    try:
        CustomApp.objects.get(id=app_id).delete()
    except CustomApp.DoesNotExist:
        raise HTTPError(404, "Custom app not found")
    return {"message": "Deleted"}, 200
