from __future__ import annotations

import json
import logging

from apiflask import APIBlueprint, HTTPError
from flask import g, request

from app.schemas.workflow import (
    WorkflowTemplateIn,
    WorkflowTemplateOut,
    WorkflowRunOut,
    WorkflowStartIn,
    SurveySubmitIn,
)
from app.services.rbac import require_project_role

log = logging.getLogger(__name__)


def _resolve_artifact_cache(cache_id: str | None, project):
    if not cache_id:
        return None
    from app.models.artifact import ArtifactCache
    try:
        return ArtifactCache.objects.get(id=cache_id, project=project)
    except ArtifactCache.DoesNotExist:
        return None

bp = APIBlueprint("workflows", __name__)


# ─────────────────────────────────────────────────────────────
#  Helper serialisers
# ─────────────────────────────────────────────────────────────

def _node_out(node) -> dict:
    tmpl_id = None
    tmpl_name = ""
    if node.template:
        try:
            tmpl_id = str(node.template.id)
            tmpl_name = node.template.name
        except Exception:
            pass
    return {
        "node_id": node.node_id,
        "node_type": getattr(node, "node_type", "task") or "task",
        "slug": getattr(node, "slug", "") or "",
        "label": node.label or "",
        "template_id": tmpl_id,
        "template_name": tmpl_name,
        "action_config": dict(getattr(node, "action_config", None) or {}),
        "on_success": list(node.on_success or []),
        "on_failure": list(node.on_failure or []),
        "on_always": list(node.on_always or []),
        "position_x": float(node.position_x or 0.0),
        "position_y": float(node.position_y or 0.0),
    }


def _wf_out(wf) -> dict:
    return {
        "id": str(wf.id),
        "project_id": str(wf.project.id),
        "name": wf.name,
        "description": wf.description or "",
        "nodes": [_node_out(n) for n in (wf.nodes or [])],
        "survey_vars": [
            {
                "name": sv.name,
                "title": sv.title or "",
                "description": sv.description or "",
                "type": sv.type or "string",
                "required": bool(sv.required),
                "default": sv.default or "",
                "values": list(sv.values or []),
            }
            for sv in (wf.survey_vars or [])
        ],
        "allow_parallel": bool(wf.allow_parallel),
        "suppress_success_alerts": bool(wf.suppress_success_alerts),
        "artifact_cache_id": str(wf.artifact_cache.id) if wf.artifact_cache else None,
        "created_at": wf.created_at.isoformat() if wf.created_at else None,
    }


def _node_run_out(nr, node_map: dict) -> dict:
    node = node_map.get(nr.node_id)
    label = ""
    tmpl_name = ""
    tmpl_id = None
    node_type = "task"
    on_success: list = []
    on_failure: list = []
    on_always:  list = []
    if node:
        label = node.label or ""
        node_type = getattr(node, "node_type", "task") or "task"
        on_success = list(node.on_success or [])
        on_failure = list(node.on_failure or [])
        on_always  = list(node.on_always  or [])
        if node.template:
            try:
                tmpl_name = node.template.name
                tmpl_id   = str(node.template.id)
            except Exception:
                pass
    return {
        "node_id":       nr.node_id,
        "node_type":     node_type,
        "task_id":       nr.task_id or "",
        "status":        nr.status,
        "edges_fired":   bool(nr.edges_fired),
        "error_message": getattr(nr, "error_message", "") or "",
        "template_name": tmpl_name,
        "template_id":   tmpl_id,
        "label":              label,
        "on_success":         on_success,
        "on_failure":         on_failure,
        "on_always":          on_always,
        "remote_decision":    getattr(nr, "remote_decision", "") or "",
        "remote_decided_by":  getattr(nr, "remote_decided_by", "") or "",
        "remote_decided_at":  nr.remote_decided_at.isoformat() if getattr(nr, "remote_decided_at", None) else "",
    }


def _run_out(run) -> dict:
    wf = run.workflow
    wf_id = ""
    wf_name = ""
    if wf:
        try:
            wf_id = str(wf.id)
            wf_name = wf.name
        except Exception:
            pass

    # Build node_map from WorkflowTemplate nodes for enriching node runs
    node_map: dict = {}
    if wf:
        try:
            for n in (wf.nodes or []):
                node_map[n.node_id] = n
        except Exception:
            pass

    # Enrich node_runs with live Task statuses for running tasks
    from app.models.task import Task

    enriched_node_runs = []
    for nr in (run.node_runs or []):
        nr_dict = _node_run_out(nr, node_map)
        # If the embedded status is 'running' and we have a task_id, check the real task
        if nr.task_id and nr.status == "running":
            try:
                real_task = Task.objects.get(id=nr.task_id)
                nr_dict["status"] = real_task.status
            except Exception:
                pass
        enriched_node_runs.append(nr_dict)

    return {
        "id": str(run.id),
        "workflow_id": wf_id,
        "workflow_name": wf_name,
        "project_id": str(run.project.id),
        "status": run.status,
        "node_runs": enriched_node_runs,
        "user_id": str(run.user.id) if run.user else None,
        "username": run.user.username if run.user else None,
        "survey_answers": run.survey_answers or "{}",
        "pending_approval_node_id": run.pending_approval_node_id or "",
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "start": run.start.isoformat() if run.start else None,
        "end": run.end.isoformat() if run.end else None,
    }


# ─────────────────────────────────────────────────────────────
#  Workflow Template endpoints
# ─────────────────────────────────────────────────────────────

@bp.get("/api/projects/<project_id>/workflows/")
@require_project_role("owner", "manager", "task_runner", "guest")
def list_workflows(project_id):
    from app.models.workflow import WorkflowTemplate
    wfs = WorkflowTemplate.objects(project=g.project).order_by("name")
    return {"items": [_wf_out(w) for w in wfs], "total": wfs.count()}, 200


@bp.post("/api/projects/<project_id>/workflows/")
@require_project_role("owner", "manager")
@bp.input(WorkflowTemplateIn, arg_name="body")
@bp.output(WorkflowTemplateOut, status_code=201)
def create_workflow(project_id, body):
    from app.models.workflow import WorkflowTemplate, WorkflowNode
    from app.models.template import Template
    from app.models.template import SurveyVar

    wf = WorkflowTemplate(
        project=g.project,
        name=body["name"],
        description=body.get("description", ""),
        allow_parallel=body.get("allow_parallel", False),
        suppress_success_alerts=body.get("suppress_success_alerts", False),
        artifact_cache=_resolve_artifact_cache(body.get("artifact_cache_id"), g.project),
    )

    wf.nodes = _build_nodes(body.get("nodes", []))
    wf.survey_vars = _build_survey_vars(body.get("survey_vars", []))
    wf.save()
    return _wf_out(wf)


@bp.get("/api/projects/<project_id>/workflows/<wid>")
@require_project_role("owner", "manager", "task_runner", "guest")
def get_workflow(project_id, wid):
    from app.models.workflow import WorkflowTemplate
    try:
        wf = WorkflowTemplate.objects.get(id=wid, project=g.project)
    except WorkflowTemplate.DoesNotExist:
        raise HTTPError(404, "Workflow not found")
    return _wf_out(wf), 200


@bp.put("/api/projects/<project_id>/workflows/<wid>")
@require_project_role("owner", "manager")
@bp.input(WorkflowTemplateIn, arg_name="body")
@bp.output(WorkflowTemplateOut)
def update_workflow(project_id, wid, body):
    from app.models.workflow import WorkflowTemplate
    try:
        wf = WorkflowTemplate.objects.get(id=wid, project=g.project)
    except WorkflowTemplate.DoesNotExist:
        raise HTTPError(404, "Workflow not found")

    wf.name = body["name"]
    wf.description = body.get("description", "")
    wf.allow_parallel = body.get("allow_parallel", False)
    wf.suppress_success_alerts = body.get("suppress_success_alerts", False)
    wf.artifact_cache = _resolve_artifact_cache(body.get("artifact_cache_id"), g.project)
    wf.nodes = _build_nodes(body.get("nodes", []))
    wf.survey_vars = _build_survey_vars(body.get("survey_vars", []))
    wf.save()
    return _wf_out(wf)


@bp.delete("/api/projects/<project_id>/workflows/<wid>")
@require_project_role("owner", "manager")
def delete_workflow(project_id, wid):
    from app.models.workflow import WorkflowTemplate
    try:
        wf = WorkflowTemplate.objects.get(id=wid, project=g.project)
    except WorkflowTemplate.DoesNotExist:
        raise HTTPError(404, "Workflow not found")
    wf.delete()
    return {"message": "Deleted"}, 200


@bp.post("/api/projects/<project_id>/workflows/<wid>/start")
@require_project_role("owner", "manager", "task_runner")
@bp.input(WorkflowStartIn, arg_name="body")
def start_workflow(project_id, wid, body):
    from app.models.workflow import WorkflowTemplate
    from app.models.workflow_run import WorkflowRun
    from app.tasks.run_workflow import start_workflow as start_wf_task

    try:
        wf = WorkflowTemplate.objects.get(id=wid, project=g.project)
    except WorkflowTemplate.DoesNotExist:
        raise HTTPError(404, "Workflow not found")

    if not wf.nodes:
        raise HTTPError(400, "Workflow has no nodes")

    run = WorkflowRun(
        project=g.project,
        workflow=wf,
        status="waiting",
        user=g.current_user,
        survey_answers=body.get("survey_answers", "{}"),
    )
    run.save()

    start_wf_task.delay(str(run.id))
    return _run_out(run), 201


# ─────────────────────────────────────────────────────────────
#  Workflow Run endpoints
# ─────────────────────────────────────────────────────────────

@bp.get("/api/projects/<project_id>/workflow-runs/")
@require_project_role("owner", "manager", "task_runner", "guest")
def list_workflow_runs(project_id):
    from app.models.workflow_run import WorkflowRun
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except (ValueError, TypeError):
        raise HTTPError(400, "Invalid pagination parameters")

    qs = WorkflowRun.objects(project=g.project).order_by("-created_at")
    total = qs.count()
    items = qs.skip((page - 1) * per_page).limit(per_page)
    return {
        "items": [_run_out(r) for r in items],
        "total": total,
        "page": page,
        "per_page": per_page,
    }, 200


@bp.get("/api/projects/<project_id>/workflow-runs/<run_id>")
@require_project_role("owner", "manager", "task_runner", "guest")
def get_workflow_run(project_id, run_id):
    from app.models.workflow_run import WorkflowRun
    try:
        run = WorkflowRun.objects.get(id=run_id, project=g.project)
    except WorkflowRun.DoesNotExist:
        raise HTTPError(404, "Workflow run not found")
    return _run_out(run), 200


@bp.post("/api/projects/<project_id>/workflow-runs/<run_id>/stop")
@require_project_role("owner", "manager", "task_runner")
def stop_workflow_run(project_id, run_id):
    from app.models.workflow_run import WorkflowRun
    from app.services.task_service import stop_task
    from app.models.task import Task
    import redis as redis_lib
    from app.config import settings

    try:
        run = WorkflowRun.objects.get(id=run_id, project=g.project)
    except WorkflowRun.DoesNotExist:
        raise HTTPError(404, "Workflow run not found")

    if run.status not in ("waiting", "running"):
        raise HTTPError(400, f"Cannot stop a run with status '{run.status}'")

    r = redis_lib.from_url(settings.REDIS_URL)

    # Signal all running node tasks to stop
    for nr in (run.node_runs or []):
        if nr.status in ("running",) and nr.task_id:
            try:
                task = Task.objects.get(id=nr.task_id)
                if task.status in ("waiting", "starting", "running"):
                    r.set(f"stop:{nr.task_id}", "1", ex=300)
                    if task.status == "waiting":
                        task.status = "stopped"
                        task.save()
            except Task.DoesNotExist:
                pass
            except Exception as exc:
                log.warning("Could not stop task %s: %s", nr.task_id, exc)

    run.status = "stopped"
    run.save()

    return {"message": "Stop signal sent"}, 200


@bp.get("/api/projects/<project_id>/workflow-runs/<run_id>/approval")
@require_project_role("owner", "manager", "task_runner")
def get_approval_info(project_id, run_id):
    """Return the title/text for the pending approval question node.

    Reads a JSON artifact named after the pending node_id from the workflow
    run's artifact run. Falls back to a default message if not found.
    """
    from app.models.workflow_run import WorkflowRun
    try:
        run = WorkflowRun.objects.get(id=run_id, project=g.project)
    except WorkflowRun.DoesNotExist:
        raise HTTPError(404, "Workflow run not found")

    if run.status != "waiting_approval" or not run.pending_approval_node_id:
        raise HTTPError(400, "No pending approval for this run")

    node_id = run.pending_approval_node_id
    title = "Proceed?"
    text = ""
    slug = ""

    # Resolve the slug from the workflow node definition
    try:
        wf = run.workflow
        if wf:
            for n in (wf.nodes or []):
                if n.node_id == node_id:
                    slug = getattr(n, "slug", "") or ""
                    break
    except Exception as exc:
        log.warning("Could not resolve slug for node %s: %s", node_id, exc)

    artifact_key = slug if slug else node_id

    # Try to read artifact named after the slug (or node_id as fallback)
    if run.artifact_run:
        try:
            from app.models.artifact import Artifact
            import json as _json
            art = Artifact.objects(run=run.artifact_run, name=artifact_key, artifact_type="json").first()
            if art and art.json_data:
                data = _json.loads(art.json_data)
                title = data.get("title", title)
                text = data.get("text", text)
        except Exception as exc:
            log.warning("Could not read approval artifact '%s': %s", artifact_key, exc)

    # Determine the node type so the frontend can distinguish question vs remote_approval
    node_type = "question"
    emails: list = []
    try:
        wf = run.workflow
        if wf:
            for n in (wf.nodes or []):
                if n.node_id == node_id:
                    node_type = getattr(n, "node_type", "question") or "question"
                    emails = (n.action_config or {}).get("emails", [])
                    break
    except Exception:
        pass

    # For remote_approval, also include who decided (if available)
    remote_decision = ""
    remote_decided_by = ""
    for nr in (run.node_runs or []):
        if nr.node_id == node_id:
            remote_decision = nr.remote_decision or ""
            remote_decided_by = nr.remote_decided_by or ""
            break

    return {
        "node_id": node_id,
        "slug": slug,
        "artifact_key": artifact_key,
        "title": title,
        "text": text,
        "node_type": node_type,
        "emails": emails,
        "remote_decision": remote_decision,
        "remote_decided_by": remote_decided_by,
    }, 200


@bp.post("/api/projects/<project_id>/workflow-runs/<run_id>/approve")
@require_project_role("owner", "manager", "task_runner")
def approve_workflow_run(project_id, run_id):
    """Approve the pending question node — workflow continues."""
    import datetime as _dt
    from app.models.workflow_run import WorkflowRun
    from app.tasks.run_workflow import advance_workflow

    try:
        run = WorkflowRun.objects.get(id=run_id, project=g.project)
    except WorkflowRun.DoesNotExist:
        raise HTTPError(404, "Workflow run not found")

    if run.status != "waiting_approval" or not run.pending_approval_node_id:
        raise HTTPError(400, "No pending approval for this run")

    node_id = run.pending_approval_node_id
    for nr in (run.node_runs or []):
        if nr.node_id == node_id:
            nr.status = "success"
            nr.edges_fired = False  # advance_workflow will fire edges
            break

    run.status = "running"
    run.pending_approval_node_id = ""
    run.save()

    advance_workflow.apply_async(args=[str(run.id)], countdown=1)
    return {"message": "Approved"}, 200


@bp.post("/api/projects/<project_id>/workflow-runs/<run_id>/reject")
@require_project_role("owner", "manager", "task_runner")
def reject_workflow_run(project_id, run_id):
    """Reject the pending question node — workflow is stopped."""
    import datetime as _dt
    from app.models.workflow_run import WorkflowRun

    try:
        run = WorkflowRun.objects.get(id=run_id, project=g.project)
    except WorkflowRun.DoesNotExist:
        raise HTTPError(404, "Workflow run not found")

    if run.status != "waiting_approval" or not run.pending_approval_node_id:
        raise HTTPError(400, "No pending approval for this run")

    node_id = run.pending_approval_node_id
    for nr in (run.node_runs or []):
        if nr.node_id == node_id:
            nr.status = "stopped"
            nr.edges_fired = True
        elif nr.status == "pending":
            nr.status = "skipped"
            nr.edges_fired = True

    run.status = "stopped"
    run.pending_approval_node_id = ""
    run.end = _dt.datetime.utcnow()
    run.save()

    try:
        from app.services.notify_service import notify_workflow_result
        notify_workflow_result(run)
    except Exception as exc:
        log.error("Workflow notification dispatch error: %s", exc)

    return {"message": "Rejected"}, 200


def _find_wf_node(wf, node_id: str):
    try:
        if not wf:
            return None
        for n in (wf.nodes or []):
            if n.node_id == node_id:
                return n
    except Exception as exc:
        log.warning("Could not resolve workflow node %s: %s", node_id, exc)
    return None


@bp.get("/api/projects/<project_id>/workflow-runs/<run_id>/survey")
@require_project_role("owner", "manager", "task_runner")
def get_survey_schema(project_id, run_id):
    """Return the dynamic survey form schema for the pending survey node.

    Reads a JSON artifact named after the node's configured
    `input_artifact_name` from the workflow run's artifact run.
    """
    from app.models.workflow_run import WorkflowRun
    try:
        run = WorkflowRun.objects.get(id=run_id, project=g.project)
    except WorkflowRun.DoesNotExist:
        raise HTTPError(404, "Workflow run not found")

    if run.status != "waiting_approval" or not run.pending_approval_node_id:
        raise HTTPError(400, "No pending survey for this run")

    node_id = run.pending_approval_node_id
    node = _find_wf_node(run.workflow, node_id)
    if not node or getattr(node, "node_type", "") != "survey":
        raise HTTPError(400, "Pending node is not a survey")

    input_name = (node.action_config or {}).get("input_artifact_name", "")
    output_name = (node.action_config or {}).get("output_artifact_name", "")
    schema: dict = {}

    if input_name and run.artifact_run:
        try:
            from app.models.artifact import Artifact
            art = Artifact.objects(
                run=run.artifact_run, name=input_name, artifact_type="json"
            ).order_by("-created_at").first()
            if art and art.json_data:
                schema = json.loads(art.json_data)
        except Exception as exc:
            log.warning("Could not read survey schema artifact '%s': %s", input_name, exc)

    return {
        "node_id": node_id,
        "input_artifact_name": input_name,
        "output_artifact_name": output_name,
        "schema": schema,
    }, 200


@bp.post("/api/projects/<project_id>/workflow-runs/<run_id>/survey-submit")
@require_project_role("owner", "manager", "task_runner")
@bp.input(SurveySubmitIn, arg_name="body")
def submit_survey(project_id, run_id, body):
    """Submit survey answers — stores them as a JSON artifact and resumes the workflow."""
    from app.models.workflow_run import WorkflowRun
    from app.tasks.run_workflow import advance_workflow

    try:
        run = WorkflowRun.objects.get(id=run_id, project=g.project)
    except WorkflowRun.DoesNotExist:
        raise HTTPError(404, "Workflow run not found")

    if run.status != "waiting_approval" or not run.pending_approval_node_id:
        raise HTTPError(400, "No pending survey for this run")

    node_id = run.pending_approval_node_id
    node = _find_wf_node(run.workflow, node_id)
    if not node or getattr(node, "node_type", "") != "survey":
        raise HTTPError(400, "Pending node is not a survey")

    output_name = (node.action_config or {}).get("output_artifact_name", "")
    if output_name and run.artifact_run:
        from app.services.artifact_service import store_json
        store_json(run.artifact_run, output_name, body["answers"])

    for nr in (run.node_runs or []):
        if nr.node_id == node_id:
            nr.status = "success"
            nr.edges_fired = False  # advance_workflow will fire edges
            break

    run.status = "running"
    run.pending_approval_node_id = ""
    run.save()

    advance_workflow.apply_async(args=[str(run.id)], countdown=1)
    return {"message": "Submitted"}, 200


# ─────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────

def _build_nodes(node_dicts: list) -> list:
    from app.models.workflow import WorkflowNode
    from app.models.template import Template

    from app.schemas.workflow import ACTION_NODE_TYPES

    nodes = []
    for nd in node_dicts:
        node_type = nd.get("node_type", "task") or "task"
        if node_type not in {"task", "question", "remote_approval", "survey"} | ACTION_NODE_TYPES:
            node_type = "task"
        node = WorkflowNode(
            node_id=nd["node_id"],
            node_type=node_type,
            slug=nd.get("slug", "") or "",
            label=nd.get("label", ""),
            action_config=nd.get("action_config") or {},
            on_success=list(nd.get("on_success") or []),
            on_failure=list(nd.get("on_failure") or []),
            on_always=list(nd.get("on_always") or []),
            position_x=float(nd.get("position_x") or 0.0),
            position_y=float(nd.get("position_y") or 0.0),
        )
        template_id = nd.get("template_id")
        if template_id and node_type == "task":
            try:
                node.template = Template.objects.get(id=template_id)
            except Template.DoesNotExist:
                node.template = None
        nodes.append(node)
    return nodes


def _build_survey_vars(sv_dicts: list) -> list:
    from app.models.template import SurveyVar

    result = []
    for sv in sv_dicts:
        result.append(SurveyVar(
            name=sv["name"],
            title=sv.get("title", ""),
            description=sv.get("description", ""),
            type=sv.get("type", "string"),
            required=sv.get("required", False),
            default=sv.get("default", ""),
            values=list(sv.get("values") or []),
        ))
    return result
