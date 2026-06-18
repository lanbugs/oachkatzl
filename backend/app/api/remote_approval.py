"""Anonymous approval endpoints — no authentication required.

URL pattern:
  GET /api/remote-approval/<token>/approve
  GET /api/remote-approval/<token>/reject
  GET /api/remote-approval/<token>/status
"""
from __future__ import annotations

import datetime
import logging

from flask import Blueprint, make_response

log = logging.getLogger(__name__)

bp = Blueprint("remote_approval", __name__)

# ── HTML page templates ────────────────────────────────────────────────────

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Oachkatzl</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:system-ui,sans-serif;background:#f1f5f9;display:flex;align-items:center;
          justify-content:center;min-height:100vh;padding:1rem}}
    .card{{background:#fff;border-radius:1rem;box-shadow:0 4px 24px rgba(0,0,0,.08);
           padding:2.5rem;max-width:480px;width:100%;text-align:center}}
    .icon{{font-size:3rem;margin-bottom:1rem}}
    h1{{font-size:1.5rem;font-weight:700;color:#0f172a;margin-bottom:.5rem}}
    .sub{{color:#64748b;font-size:.95rem;line-height:1.6;margin-bottom:1.5rem}}
    .wf{{color:#94a3b8;font-size:.8rem;margin-top:1.5rem}}
    .meta{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:.5rem;
           padding:.75rem 1rem;font-size:.85rem;color:#475569;margin-top:1rem;text-align:left}}
    .meta strong{{color:#0f172a}}
    .pill{{display:inline-block;padding:.2rem .7rem;border-radius:9999px;font-size:.8rem;
           font-weight:600;margin-bottom:1rem}}
    .pill.green{{background:#dcfce7;color:#15803d}}
    .pill.red{{background:#fee2e2;color:#b91c1c}}
    .pill.gray{{background:#f1f5f9;color:#475569}}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h1>{title}</h1>
    <p class="sub">{message}</p>
    {extra}
    <p class="wf">{workflow}</p>
  </div>
</body>
</html>"""


def _html(title, icon, message, extra="", workflow=""):
    return _PAGE.format(title=title, icon=icon, message=message, extra=extra, workflow=workflow)


def _resp(html: str, status: int = 200):
    r = make_response(html, status)
    r.headers["Content-Type"] = "text/html; charset=utf-8"
    return r


# ── Token lookup helper ────────────────────────────────────────────────────

def _load_token(token: str):
    """Return (RemoteApprovalToken, WorkflowRun, WorkflowNodeRun) or raise."""
    from app.models.remote_approval import RemoteApprovalToken
    from app.models.workflow_run import WorkflowRun

    try:
        rat = RemoteApprovalToken.objects.get(token=token)
    except RemoteApprovalToken.DoesNotExist:
        return None, None, None

    try:
        run = WorkflowRun.objects.get(id=rat.workflow_run_id)
    except WorkflowRun.DoesNotExist:
        return rat, None, None

    nr = next((n for n in (run.node_runs or []) if n.node_id == rat.node_id), None)
    return rat, run, nr


# ── Decision handler ───────────────────────────────────────────────────────

def _apply_decision(action: str, token: str):
    """Core logic shared by approve and reject endpoints."""
    rat, run, nr = _load_token(token)

    if rat is None:
        return _resp(_html(
            "Invalid link", "❌",
            "This link is invalid or has expired. Please contact the workflow owner.",
        ), 404)

    if run is None:
        return _resp(_html(
            "Workflow not found", "❌",
            "The associated workflow run could not be found. It may have been deleted.",
        ), 404)

    wf_name = ""
    try:
        wf_name = run.workflow.name if run.workflow else ""
    except Exception:
        pass

    # Already decided?
    if nr and nr.remote_decision:
        verb = "approved" if nr.remote_decision == "approved" else "rejected"
        pill_cls = "green" if verb == "approved" else "red"
        when = ""
        if nr.remote_decided_at:
            when = nr.remote_decided_at.strftime("%Y-%m-%d %H:%M UTC")
        extra = (
            f'<span class="pill {pill_cls}">{verb}</span>'
            f'<div class="meta">'
            f'<strong>Decision by:</strong> {nr.remote_decided_by or "—"}<br>'
            f'<strong>Time:</strong> {when}'
            f'</div>'
        )
        return _resp(_html(
            "Decision already recorded", "ℹ️",
            f"This workflow has already been <strong>{verb}</strong>. "
            "No further action is needed from you.",
            extra=extra,
            workflow=wf_name,
        ))

    # Run is no longer in a state that accepts a decision?
    if run.status not in ("waiting_approval", "running"):
        return _resp(_html(
            "Workflow already completed", "ℹ️",
            f"This workflow run has already finished with status <strong>{run.status}</strong>.",
            workflow=wf_name,
        ))

    if nr is None or nr.status != "waiting_approval":
        return _resp(_html(
            "Nothing to decide", "ℹ️",
            "This node is no longer waiting for a decision.",
            workflow=wf_name,
        ))

    # Record decision
    now = datetime.datetime.utcnow()
    nr.remote_decision = "approved" if action == "approve" else "rejected"
    nr.remote_decided_by = rat.email
    nr.remote_decided_at = now

    if action == "approve":
        nr.status = "success"
        nr.edges_fired = True
        run.pending_approval_node_id = ""
        run.status = "running"
        run.node_runs = list(run.node_runs)
        run.save()
        log.info("Remote approval APPROVED by %s for run %s node %s",
                 rat.email, run.id, rat.node_id)
        # Continue the workflow
        try:
            from app.tasks.run_workflow import advance_workflow
            advance_workflow.apply_async(args=[str(run.id)], countdown=1)
        except Exception as exc:
            log.error("Failed to re-trigger advance_workflow: %s", exc)

        # Log event
        try:
            from app.models.event import Event
            Event(
                project=run.project,
                object_type="workflow_run",
                object_id=str(run.id),
                action="remote_approved",
                description=f"Remote approval approved by {rat.email}",
            ).save()
        except Exception:
            pass

        return _resp(_html(
            "Approved", "✅",
            "Thank you — the workflow will continue.",
            extra='<span class="pill green">Approved</span>',
            workflow=wf_name,
        ))

    else:  # reject
        nr.status = "stopped"
        nr.edges_fired = True
        for other in run.node_runs:
            if other.node_id != nr.node_id and other.status == "pending":
                other.status = "skipped"
                other.edges_fired = True
        run.pending_approval_node_id = ""
        run.status = "stopped"
        run.end = now
        run.node_runs = list(run.node_runs)
        run.save()
        log.info("Remote approval REJECTED by %s for run %s node %s",
                 rat.email, run.id, rat.node_id)

        try:
            from app.services.notify_service import notify_workflow_result
            notify_workflow_result(run)
        except Exception as exc:
            log.error("Notification after remote reject failed: %s", exc)

        try:
            from app.models.event import Event
            Event(
                project=run.project,
                object_type="workflow_run",
                object_id=str(run.id),
                action="remote_rejected",
                description=f"Remote approval rejected by {rat.email}",
            ).save()
        except Exception:
            pass

        return _resp(_html(
            "Rejected", "🛑",
            "You have rejected this workflow run. It has been stopped.",
            extra='<span class="pill red">Rejected</span>',
            workflow=wf_name,
        ))


# ── Endpoints ──────────────────────────────────────────────────────────────

@bp.get("/api/remote-approval/<token>/approve")
def approve(token: str):
    return _apply_decision("approve", token)


@bp.get("/api/remote-approval/<token>/reject")
def reject(token: str):
    return _apply_decision("reject", token)


@bp.get("/api/remote-approval/<token>/status")
def status(token: str):
    rat, run, nr = _load_token(token)

    if rat is None:
        return _resp(_html("Invalid link", "❌", "This link is invalid or has expired."), 404)

    wf_name = ""
    try:
        wf_name = run.workflow.name if run and run.workflow else ""
    except Exception:
        pass

    if nr and nr.remote_decision:
        verb = "approved" if nr.remote_decision == "approved" else "rejected"
        pill_cls = "green" if verb == "approved" else "red"
        when = nr.remote_decided_at.strftime("%Y-%m-%d %H:%M UTC") if nr.remote_decided_at else ""
        extra = (
            f'<span class="pill {pill_cls}">{verb}</span>'
            f'<div class="meta">'
            f'<strong>Decision by:</strong> {nr.remote_decided_by or "—"}<br>'
            f'<strong>Time:</strong> {when}'
            f'</div>'
        )
        return _resp(_html(
            "Decision recorded", "ℹ️",
            f"This workflow has been <strong>{verb}</strong>.",
            extra=extra, workflow=wf_name,
        ))

    base_url = ""
    try:
        from app.config import settings
        base_url = settings.BASE_URL.rstrip("/")
    except Exception:
        pass

    approve_url = f"{base_url}/api/remote-approval/{rat.token}/approve"
    reject_url = f"{base_url}/api/remote-approval/{rat.token}/reject"

    extra = (
        f'<span class="pill gray">Pending</span>'
        f'<div style="display:flex;gap:.75rem;justify-content:center;margin-top:1rem">'
        f'<a href="{approve_url}" style="background:#16a34a;color:#fff;padding:.6rem 1.5rem;'
        f'border-radius:.5rem;text-decoration:none;font-weight:600">✓ Approve</a>'
        f'<a href="{reject_url}" style="background:#dc2626;color:#fff;padding:.6rem 1.5rem;'
        f'border-radius:.5rem;text-decoration:none;font-weight:600">✗ Reject</a>'
        f'</div>'
    )
    return _resp(_html(
        "Approval required", "❓",
        "Please review and make a decision for this workflow run.",
        extra=extra, workflow=wf_name,
    ))
