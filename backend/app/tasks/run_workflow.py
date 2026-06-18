from __future__ import annotations

import datetime
import json
import logging

log = logging.getLogger(__name__)

from app.celery_app import celery

# Statuses that indicate a node/run has finished (no further state changes expected)
TERMINAL: frozenset[str] = frozenset({"success", "error", "stopped", "skipped"})

ACTION_NODE_TYPES: frozenset[str] = frozenset(
    {"list_generator", "pdf_generator", "send_mail", "transfer_file"}
)

CONTROL_NODE_TYPES: frozenset[str] = frozenset({"question", "remote_approval"})


def _ensure_mongo() -> None:
    """Connect to MongoDB if not already connected."""
    import mongoengine
    from mongoengine.connection import get_connection
    from app.config import settings

    try:
        get_connection().server_info()
    except Exception:
        mongoengine.disconnect_all()
        mongoengine.connect(host=settings.MONGO_URI)


# ─────────────────────────────────────────────────────────────────────────────
# Incoming-edge index
# ─────────────────────────────────────────────────────────────────────────────

def _build_incoming(wf_nodes: list) -> dict[str, dict[str, set[str]]]:
    """Return  target_node_id → { src_node_id → {edge_types} }.

    edge_types is a subset of {"success", "failure", "always"}.
    """
    index: dict[str, dict[str, set[str]]] = {}
    for n in wf_nodes:
        for t in (n.on_success or []):
            index.setdefault(t, {}).setdefault(n.node_id, set()).add("success")
        for t in (n.on_failure or []):
            index.setdefault(t, {}).setdefault(n.node_id, set()).add("failure")
        for t in (n.on_always or []):
            index.setdefault(t, {}).setdefault(n.node_id, set()).add("always")
    return index


# ─────────────────────────────────────────────────────────────────────────────
# AND-join target-readiness decision
# ─────────────────────────────────────────────────────────────────────────────

def _target_decision(
    target_id: str,
    incoming: dict[str, dict[str, set[str]]],
    nr_map: dict,
) -> str:
    """Return 'start', 'wait', or 'skip' for a pending target node.

    AND-join semantics: every predecessor must have edges_fired=True and
    voted 'yes' before the target may start.

    A predecessor votes 'yes' when at least one of its edge types to the
    target fires given its outcome (success/failure/always).
    A predecessor votes 'no' when done but none of its edges fire.

    Call this AFTER Step 2a has marked all completed nodes with edges_fired=True
    so the decision reflects the fully-updated state.
    """
    predecessors = incoming.get(target_id, {})
    if not predecessors:
        return "start"   # root node (no predecessors) — start it

    for src_id, edge_types in predecessors.items():
        src_nr = nr_map.get(src_id)
        if src_nr is None:
            continue   # unknown predecessor — skip it

        if not src_nr.edges_fired or src_nr.status not in TERMINAL:
            return "wait"   # predecessor hasn't finished/fired yet

        # Predecessor done and fired — does at least one edge fire?
        votes_yes = (
            "always" in edge_types
            or ("success" in edge_types and src_nr.status == "success")
            or ("failure" in edge_types and src_nr.status in ("error", "stopped"))
        )
        if not votes_yes:
            return "skip"   # predecessor voted no → target is unreachable

    return "start"


# ─────────────────────────────────────────────────────────────────────────────
# Final-status helpers
# ─────────────────────────────────────────────────────────────────────────────

def _error_is_handled(node_id: str, node_map: dict, nr_map: dict, visited: set) -> bool:
    """Return True if the failure at node_id is caught by a successor."""
    if node_id in visited:
        return False
    visited.add(node_id)

    node = node_map.get(node_id)
    if not node:
        return False

    handler_ids = list(node.on_failure or []) + list(node.on_always or [])
    if not handler_ids:
        return False

    for hid in handler_ids:
        hnr = nr_map.get(hid)
        if not hnr:
            continue
        if hnr.status == "success":
            return True
        if hnr.status in ("error", "stopped"):
            if _error_is_handled(hid, node_map, nr_map, set(visited)):
                return True

    return False


def _final_status(node_runs: list, node_map: dict, nr_map: dict) -> str:
    """Derive overall workflow status.

    'error' if any node failed without a handler path that ran to success.
    'success' if every failure was absorbed by a defined on_failure/on_always path.
    """
    for nr in node_runs:
        if nr.status in ("error", "stopped"):
            if not _error_is_handled(nr.node_id, node_map, nr_map, set()):
                return "error"
    return "success"


# ─────────────────────────────────────────────────────────────────────────────
# Root-node detection
# ─────────────────────────────────────────────────────────────────────────────

def _find_root_nodes(wf_nodes: list) -> list[str]:
    """Return node_ids that are not referenced as a target in any edge."""
    all_ids = {n.node_id for n in wf_nodes}
    referenced: set[str] = set()
    for n in wf_nodes:
        for nid in (n.on_success or []):
            referenced.add(nid)
        for nid in (n.on_failure or []):
            referenced.add(nid)
        for nid in (n.on_always or []):
            referenced.add(nid)
    return [nid for nid in all_ids if nid not in referenced]


# ─────────────────────────────────────────────────────────────────────────────
# Task creation helper
# ─────────────────────────────────────────────────────────────────────────────

def _start_node_task(node, run, survey_dict: dict, artifact_run=None):
    """Create and enqueue a Task for a single workflow node.

    Returns the created Task, or None if the node has no template or task
    creation fails.
    """
    from app.services.task_service import create_task, enqueue_task

    if not node.template:
        log.warning("Node %s has no template — skipping", node.node_id)
        return None

    try:
        _ = node.template.id
    except Exception:
        log.warning("Node %s template reference is broken — skipping", node.node_id)
        return None

    try:
        task = create_task(
            template=node.template,
            user=run.user,
            survey_answers=survey_dict,
            triggered_by="workflow",
            trigger_name=str(run.id),
            artifact_run=artifact_run,
        )
        enqueue_task(task)
        return task
    except Exception as exc:
        log.error("Failed to create task for node %s: %s", node.node_id, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Action node executor
# ─────────────────────────────────────────────────────────────────────────────

def _get_approval_content(node, run) -> tuple[str, str]:
    """Return (title, text) from artifact for approval nodes."""
    slug = getattr(node, "slug", "") or (node.action_config or {}).get("slug", "")
    log.debug("_get_approval_content: slug=%r artifact_run=%r", slug, run.artifact_run)
    if not slug:
        log.warning("_get_approval_content: slug is empty — returning default")
        return "Proceed?", ""
    if not run.artifact_run:
        log.warning("_get_approval_content: run.artifact_run is None — returning default")
        return "Proceed?", ""
    try:
        from app.models.artifact import Artifact
        art = Artifact.objects(
            run=run.artifact_run,
            name=slug,
            artifact_type="json",
        ).order_by("-created_at").first()
        log.debug("_get_approval_content: artifact lookup name=%r → %s", slug, art)
        if art and art.json_data:
            import json as _json
            d = _json.loads(art.json_data)
            return d.get("title", "Proceed?"), d.get("text", "")
        log.warning("_get_approval_content: artifact '%s' not found or empty json_data", slug)
    except Exception as exc:
        log.warning("_get_approval_content: exception: %s", exc)
    return "Proceed?", ""


def _send_remote_approval_emails(node, run) -> None:
    """Generate tokens for each configured email and send approval emails."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    from app.config import settings
    from app.models.remote_approval import RemoteApprovalToken
    from app.models.option import Option

    emails: list[str] = (node.action_config or {}).get("emails", [])
    if not emails:
        log.warning("remote_approval node %s has no emails configured", node.node_id)
        return

    def _opt(key, default=""):
        try:
            o = Option.objects(key=key).first()
            return o.value if o else default
        except Exception:
            return default

    smtp_host = _opt("SMTP_HOST")
    if not smtp_host:
        log.warning("remote_approval: SMTP_HOST not set — skipping email")
        return

    smtp_port = int(_opt("SMTP_PORT", "587"))
    smtp_user = _opt("SMTP_USER")
    smtp_pass = _opt("SMTP_PASSWORD")
    smtp_from = _opt("SMTP_FROM") or smtp_user or "oachkatzl@localhost"
    use_tls = _opt("SMTP_TLS", "true").lower() != "false"

    title, text = _get_approval_content(node, run)
    base_url = settings.BASE_URL.rstrip("/")

    wf_name = ""
    try:
        wf_name = run.workflow.name if run.workflow else ""
    except Exception:
        pass

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            if use_tls:
                smtp.starttls()
            if smtp_user:
                smtp.login(smtp_user, smtp_pass)

            for email in emails:
                rat = RemoteApprovalToken.generate(
                    workflow_run_id=str(run.id),
                    node_id=node.node_id,
                    email=email,
                )
                approve_url = f"{base_url}/api/remote-approval/{rat.token}/approve"
                reject_url = f"{base_url}/api/remote-approval/{rat.token}/reject"

                plain = (
                    f"{title}\n\n"
                    f"{text}\n\n"
                    f"Approve: {approve_url}\n"
                    f"Reject:  {reject_url}\n\n"
                    f"Workflow: {wf_name}\n"
                    f"Once a decision is made, all other links become inactive."
                )
                html = f"""<html><body style="font-family:system-ui,sans-serif;color:#0f172a;max-width:560px;margin:auto;padding:2rem">
<h2 style="margin-bottom:.5rem">&#10067; {title}</h2>
{"<p style='color:#475569;margin-bottom:1.5rem;white-space:pre-wrap'>" + text + "</p>" if text else ""}
<div style="display:flex;gap:1rem;margin:1.5rem 0">
  <a href="{approve_url}" style="background:#16a34a;color:#fff;padding:.7rem 1.5rem;border-radius:.5rem;text-decoration:none;font-weight:600">&#10003; Approve</a>
  <a href="{reject_url}" style="background:#dc2626;color:#fff;padding:.7rem 1.5rem;border-radius:.5rem;text-decoration:none;font-weight:600">&#10007; Reject</a>
</div>
<p style="color:#94a3b8;font-size:.8rem">Workflow: {wf_name} &mdash; Once a decision is made, all other links become inactive.</p>
</body></html>"""

                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"[Approval Required] {title}"
                msg["From"] = smtp_from
                msg["To"] = email
                msg.attach(MIMEText(plain, "plain"))
                msg.attach(MIMEText(html, "html"))
                smtp.send_message(msg)
                log.info("Remote approval email sent to %s for run %s", email, run.id)
    except Exception as exc:
        log.error("Failed to send remote approval emails: %s", exc, exc_info=True)


def _execute_action_node(node, run) -> None:
    """Dispatch to the appropriate action_nodes handler."""
    from app.tasks.action_nodes import (
        execute_list_generator,
        execute_pdf_generator,
        execute_send_mail,
        execute_transfer_file,
    )

    cfg = dict(getattr(node, "action_config", None) or {})
    nt = node.node_type

    if nt == "list_generator":
        execute_list_generator(cfg, run)
    elif nt == "pdf_generator":
        execute_pdf_generator(cfg, run)
    elif nt == "send_mail":
        execute_send_mail(cfg, run)
    elif nt == "transfer_file":
        execute_transfer_file(cfg, run, node)
    else:
        raise ValueError(f"Unknown action node type: {nt}")


# ─────────────────────────────────────────────────────────────────────────────
# Celery tasks
# ─────────────────────────────────────────────────────────────────────────────

@celery.task(bind=True, name="start_workflow")
def start_workflow(self, workflow_run_id: str) -> None:
    _ensure_mongo()

    from app.models.workflow_run import WorkflowRun, WorkflowNodeRun

    try:
        run = WorkflowRun.objects.get(id=workflow_run_id)
    except WorkflowRun.DoesNotExist:
        log.error("WorkflowRun %s not found", workflow_run_id)
        return

    try:
        wf = run.workflow
        if not wf:
            log.error("WorkflowRun %s has no workflow", workflow_run_id)
            run.status = "error"
            run.save()
            return

        try:
            survey_dict = json.loads(run.survey_answers or "{}")
        except (json.JSONDecodeError, TypeError):
            survey_dict = {}

        # Create a shared ArtifactRun for the whole workflow run (if cache configured)
        artifact_run = None
        try:
            cache = wf.artifact_cache
            if cache:
                import redis as _redis_lib
                from app.config import settings as _cfg
                from app.services.artifact_service import create_artifact_run
                artifact_run, raw_token = create_artifact_run(cache=cache, workflow_run=run)
                run.artifact_run = artifact_run
                _r = _redis_lib.from_url(_cfg.REDIS_URL)
                _r.setex(f"artifact_token:{artifact_run.id}", 3600, raw_token)
        except Exception as exc:
            log.warning("Artifact run setup failed for workflow %s: %s", workflow_run_id, exc)
            artifact_run = None

        # Initialise a WorkflowNodeRun for every node
        node_runs = [
            WorkflowNodeRun(node_id=n.node_id, status="pending")
            for n in (wf.nodes or [])
        ]
        node_map = {n.node_id: n for n in (wf.nodes or [])}
        nr_map = {nr.node_id: nr for nr in node_runs}

        for root_id in _find_root_nodes(wf.nodes or []):
            node = node_map.get(root_id)
            nr = nr_map.get(root_id)
            if node is None or nr is None:
                continue
            task = _start_node_task(node, run, survey_dict, artifact_run=artifact_run)
            if task is not None:
                nr.status = "running"
                nr.task_id = str(task.id)
            else:
                nr.status = "skipped"

        run.node_runs = node_runs          # explicit assign — no tracking ambiguity
        run.status = "running"
        run.start = datetime.datetime.utcnow()
        run.save()

        advance_workflow.apply_async(args=[workflow_run_id], countdown=3)

    except Exception as exc:
        log.error("start_workflow %s crashed: %s", workflow_run_id, exc, exc_info=True)
        try:
            run.status = "error"
            run.save()
        except Exception:
            pass


@celery.task(bind=True, name="advance_workflow")
def advance_workflow(self, workflow_run_id: str) -> None:
    _ensure_mongo()

    from app.models.workflow_run import WorkflowRun
    from app.models.task import Task

    try:
        run = WorkflowRun.objects.get(id=workflow_run_id)
    except WorkflowRun.DoesNotExist:
        log.error("WorkflowRun %s not found in advance_workflow", workflow_run_id)
        return

    if run.status in TERMINAL:
        return

    try:
        wf = run.workflow
        if not wf:
            run.status = "error"
            run.save()
            return

        node_map = {n.node_id: n for n in (wf.nodes or [])}

        # Build nr_map from a SINGLE pass — ALL state changes go through nr_map.
        # We reassign run.node_runs from nr_map before every save so mongoengine
        # change-tracking ambiguity cannot cause stale data to be written.
        nr_map = {nr.node_id: nr for nr in (run.node_runs or [])}

        incoming = _build_incoming(wf.nodes or [])

        try:
            survey_dict = json.loads(run.survey_answers or "{}")
        except (json.JSONDecodeError, TypeError):
            survey_dict = {}

        # ── Step 1: Sync running nodes from real Task documents ───────────
        for nr in nr_map.values():
            if nr.status == "running" and nr.task_id:
                try:
                    real_task = Task.objects.get(id=nr.task_id)
                    if real_task.status in TERMINAL:
                        nr.status = real_task.status
                except Task.DoesNotExist:
                    log.warning("Task %s not found for node %s — marking error",
                                nr.task_id, nr.node_id)
                    nr.status = "error"
                except Exception as exc:
                    log.warning("Could not load task %s: %s", nr.task_id, exc)

        # ── Steps 2a+2b: propagate skip/start decisions until stable ─────
        #
        # Root cause of the "pending forever" bug: Step 2a was marking only
        # ("success","error","stopped") as edges_fired, leaving "skipped" out.
        # Downstream nodes then saw edges_fired=False on a skipped predecessor
        # and returned "wait" indefinitely.
        #
        # Fix: use TERMINAL (which already includes "skipped") in Step 2a and
        # set edges_fired=True immediately when skipping a node in Step 2b.
        # The while-loop propagates full skip chains in a single advance call
        # instead of requiring one call per depth level.
        changed = True
        while changed:
            changed = False

            # 2a — mark every terminal node (incl. "skipped") as fired
            for nr in nr_map.values():
                if nr.status in TERMINAL and not nr.edges_fired:
                    nr.edges_fired = True
                    changed = True

            # 2b — resolve every pending node
            for nr in list(nr_map.values()):
                if nr.status != "pending":
                    continue

                node = node_map.get(nr.node_id)
                decision = _target_decision(nr.node_id, incoming, nr_map)

                if decision == "start":
                    log.debug("Workflow %s: starting node %s", workflow_run_id, nr.node_id)
                    node_type = getattr(node, "node_type", "task") if node else "task"
                    if node and node_type == "question":
                        # Pause for user approval — advance_workflow will not be rescheduled
                        log.info("Workflow %s: question node %s reached, pausing for approval",
                                 workflow_run_id, nr.node_id)
                        nr.status = "waiting_approval"
                        changed = True
                    elif node and node_type == "remote_approval":
                        log.info("Workflow %s: remote_approval node %s reached, sending emails",
                                 workflow_run_id, nr.node_id)
                        nr.status = "waiting_approval"
                        changed = True
                        # Save state before sending emails so tokens can reference the run
                        run.node_runs = list(nr_map.values())
                        run.pending_approval_node_id = nr.node_id
                        run.status = "waiting_approval"
                        run.save()
                        _send_remote_approval_emails(node, run)
                        return  # token endpoint will call advance_workflow when decided
                    elif node and node_type in ACTION_NODE_TYPES:
                        nr.status = "running"
                        changed = True
                        # Save running state before executing so it's visible in the UI
                        run.node_runs = list(nr_map.values())
                        run.save()
                        try:
                            _execute_action_node(node, run)
                            nr.status = "success"
                            nr.error_message = ""
                        except Exception as exc:
                            log.error("Action node %s failed: %s", nr.node_id, exc, exc_info=True)
                            nr.status = "error"
                            nr.error_message = str(exc)
                        nr.edges_fired = True
                    elif node:
                        wf_artifact_run = run.artifact_run if run.artifact_run else None
                        task = _start_node_task(node, run, survey_dict, artifact_run=wf_artifact_run)
                        if task is not None:
                            nr.status = "running"
                            nr.task_id = str(task.id)
                        else:
                            nr.status = "skipped"
                            nr.edges_fired = True
                        changed = True
                    else:
                        log.warning("Node %s missing from workflow — skipping", nr.node_id)
                        nr.status = "skipped"
                        nr.edges_fired = True
                        changed = True

                elif decision == "skip":
                    preds = incoming.get(nr.node_id, {})
                    reasons = [
                        f"{pid[:8]} status={nr_map[pid].status} edges={etypes}"
                        for pid, etypes in preds.items()
                        if pid in nr_map
                    ]
                    log.warning(
                        "Workflow %s: skipping node %s — predecessor votes: %s",
                        workflow_run_id, nr.node_id, "; ".join(reasons) or "none",
                    )
                    nr.status = "skipped"
                    nr.edges_fired = True   # fire immediately so successors can evaluate
                    changed = True
                # decision == "wait": nothing to do this iteration

        # ── Step 3: Finalize or reschedule ───────────────────────────────
        # Always assign from nr_map to avoid mongoengine tracking ambiguity
        run.node_runs = list(nr_map.values())

        # Check if a question node is waiting for approval — halt polling until user decides
        approval_nr = next((nr for nr in nr_map.values() if nr.status == "waiting_approval"), None)
        if approval_nr:
            run.status = "waiting_approval"
            run.pending_approval_node_id = approval_nr.node_id
            run.save()
            return  # approve/reject API will re-trigger advance_workflow

        non_terminal = [nr for nr in nr_map.values() if nr.status not in TERMINAL]
        if not non_terminal:
            nr_map_final = {nr.node_id: nr for nr in nr_map.values()}
            run.status = _final_status(list(nr_map.values()), node_map, nr_map_final)
            run.end = datetime.datetime.utcnow()
            run.save()
            try:
                from app.services.notify_service import notify_workflow_result
                notify_workflow_result(run)
            except Exception as exc:
                log.error("Workflow notification dispatch error: %s", exc)
            return

        run.save()

        if run.status == "running":
            advance_workflow.apply_async(args=[workflow_run_id], countdown=3)

    except Exception as exc:
        log.error("advance_workflow %s crashed: %s", workflow_run_id, exc, exc_info=True)
        try:
            run.save()
        except Exception:
            pass
        try:
            if run.status == "running":
                advance_workflow.apply_async(args=[workflow_run_id], countdown=5)
        except Exception:
            pass
