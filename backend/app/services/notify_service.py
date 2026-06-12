"""Notification service — sends alerts when tasks complete."""
from __future__ import annotations

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────

_SENSITIVE_OPTION_KEYS = {"SMTP_PASSWORD"}


def _get_option(key: str, default: str = "") -> str:
    from app.models.option import Option
    opt = Option.objects(key=key).first()
    value = opt.value if opt else default
    if key in _SENSITIVE_OPTION_KEYS and value:
        from app.services.crypto import decrypt, CryptoError
        try:
            return decrypt(value)
        except CryptoError:
            return value  # tolerate legacy unencrypted values
    return value


def _task_summary(task, template) -> str:
    duration = "—"
    if task.start and task.end:
        secs = int((task.end - task.start).total_seconds())
        duration = f"{secs // 60}m {secs % 60}s" if secs >= 60 else f"{secs}s"
    return (
        f"Template : {template.name}\n"
        f"Status   : {task.status.upper()}\n"
        f"Duration : {duration}\n"
        f"Exit code: {task.exit_code if task.exit_code is not None else '—'}\n"
        f"Commit   : {task.commit_hash[:8] if task.commit_hash else '—'}"
    )


def _task_summary_html(task, template) -> str:
    rows = [
        ("Template", template.name),
        ("Status", task.status.upper()),
        ("Exit code", str(task.exit_code) if task.exit_code is not None else "—"),
        ("Commit", task.commit_hash[:8] if task.commit_hash else "—"),
    ]
    if task.start and task.end:
        secs = int((task.end - task.start).total_seconds())
        duration = f"{secs // 60}m {secs % 60}s" if secs >= 60 else f"{secs}s"
        rows.insert(2, ("Duration", duration))

    color = "#27ae60" if task.status == "success" else "#e74c3c"
    rows_html = "".join(
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>{k}</td>"
        f"<td style='padding:4px 0'><strong>{v}</strong></td></tr>"
        for k, v in rows
    )
    return (
        f"<div style='font-family:sans-serif;max-width:600px'>"
        f"<div style='background:{color};color:#fff;padding:12px 16px;border-radius:4px 4px 0 0'>"
        f"<strong>{'✅' if task.status == 'success' else '❌'} "
        f"Task {task.status.upper()}: {template.name}</strong></div>"
        f"<div style='border:1px solid #eee;border-top:none;padding:16px;border-radius:0 0 4px 4px'>"
        f"<table>{rows_html}</table>"
        f"</div></div>"
    )


# ── Channel implementations ───────────────────────────────────────────────

def _send_slack(config: dict, task, template) -> None:
    import requests as req
    url = config.get("webhook_url", "")
    if not url:
        log.warning("Slack: no webhook_url configured")
        return
    color = "#27ae60" if task.status == "success" else "#e74c3c"
    emoji = "✅" if task.status == "success" else "❌"
    req.post(url, json={
        "attachments": [{
            "color": color,
            "title": f"{emoji} Task {task.status.upper()}: {template.name}",
            "text": _task_summary(task, template),
            "footer": "Oachkatzl",
            "ts": int(task.end.timestamp()) if task.end else None,
        }]
    }, timeout=10)


def _resolve_email_recipients(config: dict, task) -> list[str]:
    """Resolve the final list of e-mail addresses for a task notification.

    Modes (stored in config["mode"]):
    - "all_members"      → every project member's e-mail address
    - "specific_members" → only selected members (config["member_ids"])
    - "extra_only"       → only extra_emails (legacy "to" field also accepted)

    config["extra_emails"] (list of strings) is always appended.
    Legacy single-address format config["to"] is also supported.
    """
    mode        = config.get("mode", "extra_only")
    member_ids  = set(config.get("member_ids", []))
    raw_extras  = config.get("extra_emails", [])
    # legacy single-address fallback
    if not raw_extras and config.get("to"):
        raw_extras = [config["to"]]

    recipients: set[str] = {e.strip() for e in raw_extras if e.strip()}

    if mode in ("all_members", "specific_members"):
        try:
            from app.models.project import ProjectMember
            project = task.project
            for m in ProjectMember.objects(project=project).select_related():
                if mode == "all_members" or str(m.user.id) in member_ids:
                    email = getattr(m.user, "email", "") or ""
                    if email.strip():
                        recipients.add(email.strip())
        except Exception as exc:
            log.warning("Could not resolve project members for email: %s", exc)

    return sorted(recipients)


def _send_email(config: dict, task, template) -> None:
    smtp_host = _get_option("SMTP_HOST")
    if not smtp_host:
        log.warning("Email: SMTP_HOST not set in global settings — skipping")
        return

    recipients = _resolve_email_recipients(config, task)
    if not recipients:
        log.warning("Email: no recipients resolved — skipping")
        return

    smtp_port = int(_get_option("SMTP_PORT", "587"))
    smtp_user = _get_option("SMTP_USER")
    smtp_pass = _get_option("SMTP_PASSWORD")
    smtp_from = _get_option("SMTP_FROM") or smtp_user or "oachkatzl@localhost"
    use_tls   = _get_option("SMTP_TLS", "true").lower() != "false"

    emoji   = "✅" if task.status == "success" else "❌"
    subject = f"{emoji} [{task.status.upper()}] {template.name}"

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        if use_tls:
            smtp.starttls()
        if smtp_user:
            smtp.login(smtp_user, smtp_pass)

        for addr in recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = smtp_from
            msg["To"]      = addr
            msg.attach(MIMEText(_task_summary(task, template), "plain"))
            msg.attach(MIMEText(_task_summary_html(task, template), "html"))
            smtp.send_message(msg)
            log.info("Email notification sent to %s", addr)


def _send_gotify(config: dict, task, template) -> None:
    import requests as req
    url = config.get("url", "").rstrip("/")
    token = config.get("token", "")
    if not url or not token:
        log.warning("Gotify: url or token missing")
        return
    priority = 5 if task.status == "success" else 8
    req.post(
        f"{url}/message",
        json={
            "title": f"[{task.status.upper()}] {template.name}",
            "message": _task_summary(task, template),
            "priority": priority,
        },
        headers={"X-Gotify-Key": token},
        timeout=10,
    )


def _send_telegram(config: dict, task, template) -> None:
    import requests as req
    bot_token = config.get("bot_token", "")
    chat_id   = config.get("chat_id", "")
    if not bot_token or not chat_id:
        log.warning("Telegram: bot_token or chat_id missing")
        return
    emoji = "✅" if task.status == "success" else "❌"
    text = (
        f"{emoji} *{template.name}* — {task.status.upper()}\n\n"
        + _task_summary(task, template)
    )
    req.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=10,
    )


def _send_teams(config: dict, task, template) -> None:
    import requests as req
    url = config.get("webhook_url", "")
    if not url:
        return
    color = "Good" if task.status == "success" else "Attention"
    emoji = "✅" if task.status == "success" else "❌"
    req.post(url, json={
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "27ae60" if task.status == "success" else "e74c3c",
        "summary": f"{emoji} {template.name} — {task.status}",
        "sections": [{"activityTitle": f"{emoji} Task {task.status.upper()}: {template.name}",
                      "text": _task_summary(task, template).replace("\n", "<br>")}],
    }, timeout=10)


SENDERS = {
    "slack":    _send_slack,
    "email":    _send_email,
    "gotify":   _send_gotify,
    "telegram": _send_telegram,
    "teams":    _send_teams,
}


# ── Workflow notification helpers ─────────────────────────────────────────

def _workflow_summary(run, wf_name: str) -> str:
    duration = "—"
    if run.start and run.end:
        secs = int((run.end - run.start).total_seconds())
        duration = f"{secs // 60}m {secs % 60}s" if secs >= 60 else f"{secs}s"
    node_runs = run.node_runs or []
    counts = {s: sum(1 for nr in node_runs if nr.status == s)
              for s in ("success", "error", "skipped", "stopped")}
    return (
        f"Workflow : {wf_name}\n"
        f"Status   : {run.status.upper()}\n"
        f"Duration : {duration}\n"
        f"Nodes    : {len(node_runs)} total · "
        f"{counts['success']} ok · {counts['error']} failed · "
        f"{counts['skipped']} skipped"
    )


def _workflow_summary_html(run, wf_name: str) -> str:
    duration = "—"
    if run.start and run.end:
        secs = int((run.end - run.start).total_seconds())
        duration = f"{secs // 60}m {secs % 60}s" if secs >= 60 else f"{secs}s"
    node_runs = run.node_runs or []
    counts = {s: sum(1 for nr in node_runs if nr.status == s)
              for s in ("success", "error", "skipped", "stopped")}
    color = "#27ae60" if run.status == "success" else "#e74c3c"
    rows = [
        ("Workflow", wf_name),
        ("Status", run.status.upper()),
        ("Duration", duration),
        ("Nodes", f"{len(node_runs)} total · {counts['success']} ok · "
                  f"{counts['error']} failed · {counts['skipped']} skipped"),
    ]
    rows_html = "".join(
        f"<tr><td style='padding:4px 12px 4px 0;color:#666'>{k}</td>"
        f"<td style='padding:4px 0'><strong>{v}</strong></td></tr>"
        for k, v in rows
    )
    emoji = "✅" if run.status == "success" else "❌"
    return (
        f"<div style='font-family:sans-serif;max-width:600px'>"
        f"<div style='background:{color};color:#fff;padding:12px 16px;border-radius:4px 4px 0 0'>"
        f"<strong>{emoji} Workflow {run.status.upper()}: {wf_name}</strong></div>"
        f"<div style='border:1px solid #eee;border-top:none;padding:16px;border-radius:0 0 4px 4px'>"
        f"<table>{rows_html}</table>"
        f"</div></div>"
    )


def _dispatch_workflow_channel(channel: str, config: dict, run, wf_name: str) -> None:
    """Send a single-channel notification for a completed workflow run."""
    import requests as req

    status = run.status
    emoji  = "✅" if status == "success" else "❌"
    title  = f"{emoji} Workflow {status.upper()}: {wf_name}"

    if channel == "slack":
        url = config.get("webhook_url", "")
        if not url:
            return
        color = "#27ae60" if status == "success" else "#e74c3c"
        req.post(url, json={"attachments": [{
            "color": color, "title": title,
            "text": _workflow_summary(run, wf_name), "footer": "Oachkatzl",
            "ts": int(run.end.timestamp()) if run.end else None,
        }]}, timeout=10)

    elif channel == "email":
        smtp_host = _get_option("SMTP_HOST")
        if not smtp_host:
            return
        smtp_port = int(_get_option("SMTP_PORT", "587"))
        smtp_user = _get_option("SMTP_USER")
        smtp_pass = _get_option("SMTP_PASSWORD")
        smtp_from = _get_option("SMTP_FROM") or smtp_user or "oachkatzl@localhost"
        use_tls   = _get_option("SMTP_TLS", "true").lower() != "false"

        # Build recipient list from extra_emails / config["to"]
        raw_extras = config.get("extra_emails", []) or ([config["to"]] if config.get("to") else [])
        recipients = sorted({e.strip() for e in raw_extras if e.strip()})
        if not recipients:
            return

        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            if use_tls:
                smtp.starttls()
            if smtp_user:
                smtp.login(smtp_user, smtp_pass)
            for addr in recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"{emoji} [WORKFLOW {status.upper()}] {wf_name}"
                msg["From"]    = smtp_from
                msg["To"]      = addr
                msg.attach(MIMEText(_workflow_summary(run, wf_name), "plain"))
                msg.attach(MIMEText(_workflow_summary_html(run, wf_name), "html"))
                smtp.send_message(msg)
                log.info("Workflow email notification sent to %s", addr)

    elif channel == "gotify":
        url   = config.get("url", "").rstrip("/")
        token = config.get("token", "")
        if not url or not token:
            return
        req.post(f"{url}/message", json={
            "title": title, "message": _workflow_summary(run, wf_name),
            "priority": 5 if status == "success" else 8,
        }, headers={"X-Gotify-Key": token}, timeout=10)

    elif channel == "telegram":
        bot_token = config.get("bot_token", "")
        chat_id   = config.get("chat_id", "")
        if not bot_token or not chat_id:
            return
        req.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id,
                  "text": f"{emoji} *{wf_name}* — {status.upper()}\n\n{_workflow_summary(run, wf_name)}",
                  "parse_mode": "Markdown"},
            timeout=10,
        )

    elif channel == "teams":
        url = config.get("webhook_url", "")
        if not url:
            return
        req.post(url, json={
            "@type": "MessageCard", "@context": "http://schema.org/extensions",
            "themeColor": "27ae60" if status == "success" else "e74c3c",
            "summary": f"{emoji} {wf_name} — {status}",
            "sections": [{"activityTitle": title,
                          "text": _workflow_summary(run, wf_name).replace("\n", "<br>")}],
        }, timeout=10)


# ── Public API ────────────────────────────────────────────────────────────

def notify_workflow_result(run) -> None:
    """Send all applicable notification rules for a completed workflow run.

    Called from advance_workflow once the run reaches a terminal status.
    Individual task notifications are suppressed for workflow tasks so that
    only this single summary fires.
    """
    from app.models.notification import NotificationSetting

    success = run.status == "success"
    try:
        wf      = run.workflow
        wf_name = wf.name if wf else "Unknown workflow"
        suppress = bool(getattr(wf, "suppress_success_alerts", False)) if wf else False
    except Exception:
        wf_name  = "Unknown workflow"
        suppress = False

    if success and suppress:
        return

    try:
        project = run.project
    except Exception:
        log.warning("notify_workflow_result: could not resolve project for run %s", run.id)
        return

    settings = list(NotificationSetting.objects(scope="global")) + \
               list(NotificationSetting.objects(scope="project", project=project))

    for setting in settings:
        if success and not setting.on_success:
            continue
        if not success and not setting.on_failure:
            continue
        try:
            config = json.loads(setting.config or "{}")
            _dispatch_workflow_channel(setting.channel, config, run, wf_name)
            log.info("Workflow notification sent channel=%s run=%s", setting.channel, run.id)
        except Exception as exc:
            log.error("Workflow notification failed channel=%s run=%s: %s",
                      setting.channel, run.id, exc)


def notify_task_result(task) -> None:
    """Send all applicable notification rules for a completed task.

    Called from run_task after the final status is written to the DB.
    Errors per channel are logged but do not affect the task result.
    """
    from app.models.notification import NotificationSetting

    success = task.status == "success"
    template = task.template
    project  = task.project

    settings = list(NotificationSetting.objects(scope="global")) + \
               list(NotificationSetting.objects(scope="project", project=project))

    for setting in settings:
        if success and not setting.on_success:
            continue
        if not success and not setting.on_failure:
            continue
        try:
            config = json.loads(setting.config or "{}")
            sender = SENDERS.get(setting.channel)
            if sender:
                sender(config, task, template)
                log.info("Notification sent channel=%s task=%s", setting.channel, task.id)
        except Exception as exc:
            log.error("Notification failed channel=%s task=%s: %s",
                      setting.channel, task.id, exc)
