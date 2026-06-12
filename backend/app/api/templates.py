from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Integer
from apiflask.schemas import Schema
from flask import g, request

from app.schemas.template import TemplateIn, TemplateOut
from app.services.rbac import require_project_role


class PaginationQuery(Schema):
    page     = Integer(load_default=1)
    per_page = Integer(load_default=20)

bp = APIBlueprint("templates", __name__, url_prefix="/api/projects/<project_id>/templates")


def _resolve_ref(model_class, id_: str | None, project=None):
    if not id_:
        return None
    try:
        kwargs = {"id": id_}
        if project is not None:
            kwargs["project"] = project
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None


def _tmpl_out(t) -> dict:
    from app.models.template import SurveyVar
    return {
        "id": str(t.id),
        "name": t.name,
        "description": t.description,
        "app": t.app,
        "type": t.type,
        "playbook": t.playbook,
        "repository_id": str(t.repository.id) if t.repository else None,
        "inventory_id": str(t.inventory.id) if t.inventory else None,
        "environment_id": str(t.environment.id) if t.environment else None,
        "arguments": t.arguments,
        "allow_override_args": t.allow_override_args,
        "allow_parallel": t.allow_parallel,
        "suppress_success_alerts": t.suppress_success_alerts,
        "view_id": str(t.view.id) if t.view else None,
        "survey_vars": [
            {
                "name": sv.name, "title": sv.title, "description": sv.description,
                "type": sv.type, "required": sv.required, "default": sv.default,
                "values": list(sv.values),
            }
            for sv in t.survey_vars
        ],
        "vaults": [
            {"vault_id": v.vault_id, "name": v.name, "key_id": str(v.key.id) if v.key else None}
            for v in t.vaults
        ],
        "start_version":     t.start_version or "",
        "build_template_id": str(t.build_template.id) if t.build_template else None,
        "autorun":           bool(t.autorun),
        "credential_ids":    [str(c.id) for c in (t.credentials or []) if c],
        "artifact_cache_id": str(t.artifact_cache.id) if t.artifact_cache else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _resolve_artifact_cache(cache_id: str | None, project):
    if not cache_id:
        return None
    from app.models.artifact import ArtifactCache
    try:
        return ArtifactCache.objects.get(id=cache_id, project=project)
    except ArtifactCache.DoesNotExist:
        return None


def _resolve_credentials(ids: list, project) -> list:
    from app.models.credential import Credential
    result = []
    for cid in (ids or []):
        try:
            result.append(Credential.objects.get(id=cid, project=project))
        except Credential.DoesNotExist:
            pass
    return result


def _build_vaults(vault_data: list, project) -> list:
    from app.models.template import VaultRef
    from app.models.access_key import AccessKey
    result = []
    for v in vault_data:
        key = None
        if v.get("key_id"):
            try:
                key = AccessKey.objects.get(id=v["key_id"], project=project)
            except AccessKey.DoesNotExist:
                pass
        result.append(VaultRef(vault_id=v["vault_id"], name=v.get("name", ""), key=key))
    return result


def _validate_app_type(app: str) -> None:
    from app.models.template import APP_TYPES
    from app.models.custom_app import CustomApp, BUILTIN_APP_TYPES
    if app not in BUILTIN_APP_TYPES:
        if not CustomApp.objects(slug=app, active=True).first():
            raise HTTPError(400, f"Unknown app type '{app}'")


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
def list_templates(project_id):
    from app.models.template import Template
    try:
        page     = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (ValueError, TypeError):
        raise HTTPError(400, "Invalid pagination parameters")
    qs    = Template.objects(project=g.project).order_by("name")
    total = qs.count()
    items = qs.skip((page - 1) * per_page).limit(per_page)
    return {"items": [_tmpl_out(t) for t in items], "total": total, "page": page, "per_page": per_page}, 200


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(TemplateIn, arg_name="body")
@bp.output(TemplateOut, status_code=201)
def create_template(project_id, body):
    from app.models.template import Template, SurveyVar
    from app.models.repository import Repository
    from app.models.inventory import Inventory
    from app.models.environment import Environment
    from app.models.view import View

    _validate_app_type(body["app"])

    survey_vars = [
        SurveyVar(
            name=sv["name"], title=sv.get("title", ""), description=sv.get("description", ""),
            type=sv.get("type", "string"), required=sv.get("required", False),
            default=sv.get("default", ""), values=sv.get("values", []),
        )
        for sv in body.get("survey_vars", [])
    ]

    t = Template(
        project=g.project,
        name=body["name"],
        description=body.get("description", ""),
        app=body["app"],
        type=body.get("type", "task"),
        playbook=body.get("playbook", ""),
        repository=_resolve_ref(Repository, body.get("repository_id"), g.project),
        inventory=_resolve_ref(Inventory, body.get("inventory_id"), g.project),
        environment=_resolve_ref(Environment, body.get("environment_id"), g.project),
        arguments=body.get("arguments", "[]"),
        allow_override_args=body.get("allow_override_args", False),
        allow_parallel=body.get("allow_parallel", False),
        suppress_success_alerts=body.get("suppress_success_alerts", False),
        view=_resolve_ref(View, body.get("view_id"), g.project),
        survey_vars=survey_vars,
        vaults=_build_vaults(body.get("vaults", []), g.project),
        start_version=body.get("start_version", "") if body.get("type") == "build" else "",
        build_template=_resolve_ref(Template, body.get("build_template_id"), g.project)
            if body.get("type") == "deploy" else None,
        autorun=body.get("autorun", False),
        credentials=_resolve_credentials(body.get("credential_ids", []), g.project),
        artifact_cache=_resolve_artifact_cache(body.get("artifact_cache_id"), g.project),
    ).save()
    return _tmpl_out(t)


@bp.get("/<template_id>")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(TemplateOut)
def get_template(project_id, template_id):
    from app.models.template import Template
    try:
        return _tmpl_out(Template.objects.get(id=template_id, project=g.project))
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")


@bp.put("/<template_id>")
@require_project_role("owner", "manager")
@bp.input(TemplateIn, arg_name="body")
@bp.output(TemplateOut)
def update_template(project_id, template_id, body):
    from app.models.template import Template, SurveyVar
    from app.models.repository import Repository
    from app.models.inventory import Inventory
    from app.models.environment import Environment
    from app.models.view import View
    try:
        t = Template.objects.get(id=template_id, project=g.project)
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")

    _validate_app_type(body["app"])

    t.name = body["name"]
    t.description = body.get("description", t.description)
    t.app = body["app"]
    t.type = body.get("type", t.type)
    t.playbook = body.get("playbook", t.playbook)
    t.repository = _resolve_ref(Repository, body.get("repository_id"), g.project)
    t.inventory = _resolve_ref(Inventory, body.get("inventory_id"), g.project)
    t.environment = _resolve_ref(Environment, body.get("environment_id"), g.project)
    t.arguments = body.get("arguments", t.arguments)
    t.allow_override_args = body.get("allow_override_args", t.allow_override_args)
    t.allow_parallel = body.get("allow_parallel", t.allow_parallel)
    t.suppress_success_alerts = body.get("suppress_success_alerts", t.suppress_success_alerts)
    t.autorun = body.get("autorun", False)
    t.view = _resolve_ref(View, body.get("view_id"), g.project)
    t.survey_vars = [
        SurveyVar(
            name=sv["name"], title=sv.get("title", ""), description=sv.get("description", ""),
            type=sv.get("type", "string"), required=sv.get("required", False),
            default=sv.get("default", ""), values=sv.get("values", []),
        )
        for sv in body.get("survey_vars", [])
    ]
    t.vaults = _build_vaults(body.get("vaults", []), g.project)
    new_type = body.get("type", t.type)
    t.start_version = body.get("start_version", t.start_version) if new_type == "build" else ""
    t.build_template = _resolve_ref(Template, body.get("build_template_id"), g.project) \
        if new_type == "deploy" else None
    t.credentials = _resolve_credentials(body.get("credential_ids", []), g.project)
    t.artifact_cache = _resolve_artifact_cache(body.get("artifact_cache_id"), g.project)
    t.save()
    return _tmpl_out(t)


# ── Completed builds for a build-type template ────────────────────────────

@bp.get("/<template_id>/builds")
@require_project_role("owner", "manager", "task_runner", "guest")
def list_builds(project_id, template_id):
    """Return completed build tasks (versions) for a build-type template.

    Used by deploy templates to let the operator pick which version to deploy.
    """
    from app.models.template import Template
    from app.models.task import Task
    try:
        tmpl = Template.objects.get(id=template_id, project=g.project)
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")

    builds = (
        Task.objects(template=tmpl, status="success")
        .order_by("-created_at")
        .limit(50)
    )
    return [
        {
            "id":          str(b.id),
            "version":     b.version or "",
            "commit_hash": b.commit_hash or "",
            "created_at":  b.created_at.isoformat() if b.created_at else None,
        }
        for b in builds
        if b.version   # only tasks that have a version recorded
    ], 200


@bp.delete("/<template_id>")
@require_project_role("owner", "manager")
def delete_template(project_id, template_id):
    from app.models.template import Template
    try:
        Template.objects.get(id=template_id, project=g.project).delete()
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")
    return {"message": "Deleted"}, 200
