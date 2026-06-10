from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import String
from apiflask.schemas import Schema
from flask import g, request

from app.services.rbac import require_project_role

bp = APIBlueprint("integrations", __name__, url_prefix="/api/projects/<project_id>/integrations")


class IntegrationIn(Schema):
    name = String(required=True)
    template_id = String(required=True)
    auth_method = String(load_default="none")
    auth_secret = String(load_default="")
    auth_header = String(load_default="")


class IntegrationOut(Schema):
    id = String()
    name = String()
    template_id = String()
    auth_method = String()
    auth_header = String()
    created_at = String()


def _out(i) -> dict:
    return {
        "id": str(i.id),
        "name": i.name,
        "template_id": str(i.template.id),
        "auth_method": i.auth_method,
        "auth_header": i.auth_header,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(IntegrationOut(many=True))
def list_integrations(project_id):
    from app.models.integration import Integration
    return [_out(i) for i in Integration.objects(project=g.project)]


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(IntegrationIn, arg_name="body")
@bp.output(IntegrationOut, status_code=201)
def create_integration(project_id, body):
    from app.models.integration import Integration
    from app.models.template import Template
    from app.services.crypto import encrypt
    try:
        tmpl = Template.objects.get(id=body["template_id"], project=g.project)
    except Template.DoesNotExist:
        raise HTTPError(404, "Template not found")
    secret_enc = encrypt(body.get("auth_secret", "")) if body.get("auth_secret") else ""
    integ = Integration(
        project=g.project, template=tmpl, name=body["name"],
        auth_method=body.get("auth_method", "none"),
        auth_secret=secret_enc,
        auth_header=body.get("auth_header", ""),
    ).save()
    return _out(integ)


@bp.delete("/<integ_id>")
@require_project_role("owner", "manager")
def delete_integration(project_id, integ_id):
    from app.models.integration import Integration
    try:
        Integration.objects.get(id=integ_id, project=g.project).delete()
    except Integration.DoesNotExist:
        raise HTTPError(404, "Integration not found")
    return {"message": "Deleted"}, 200


# ── Webhook receiver ──────────────────────────────────────────────────────

@bp.post("/webhook/<integ_id>")
def webhook_receive(project_id, integ_id):
    from app.models.integration import Integration
    from app.services.integration_service import verify_auth, check_matchers, extract_values
    from app.models.task import Task
    from app.services.task_service import create_task, enqueue_task

    try:
        integ = Integration.objects.get(id=integ_id)
    except Integration.DoesNotExist:
        raise HTTPError(404, "Integration not found")

    if not verify_auth(integ, request):
        raise HTTPError(401, "Authentication failed")

    if not check_matchers(integ, request):
        return {"message": "Matchers did not match, skipped"}, 200

    extra = extract_values(integ, request)
    task = create_task(
        template=integ.template,
        survey_answers=extra,
    )
    enqueue_task(task)
    return {"message": "Task queued", "task_id": str(task.id)}, 201
