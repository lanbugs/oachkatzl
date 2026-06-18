"""
Action node executors — called synchronously from advance_workflow.

Each function receives:
  cfg  : dict  — action_config from WorkflowNode
  run  : WorkflowRun document
  node : WorkflowNode (only transfer_file needs it)
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import logging
import smtplib
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _artifact_run(run):
    """Return the ArtifactRun for this workflow run, or None."""
    try:
        ar = run.artifact_run
        if ar:
            _ = ar.id  # force dereference
        return ar
    except Exception:
        return None


def _read_json_artifact(artifact_run, name: str):
    """Return parsed JSON data from an artifact by name, or None."""
    from app.models.artifact import Artifact
    art = Artifact.objects(run=artifact_run, name=name, artifact_type="json").first()
    if not art or not art.json_data:
        return None
    try:
        return json.loads(art.json_data)
    except Exception as exc:
        log.warning("Could not parse JSON artifact '%s': %s", name, exc)
        return None


def _read_file_artifact(artifact_run, name: str) -> bytes | None:
    """Return raw bytes from a file artifact by name, or None."""
    from app.models.artifact import Artifact
    art = Artifact.objects(run=artifact_run, name=name).first()
    if not art:
        return None
    if art.artifact_type == "json":
        return (art.json_data or "").encode()
    try:
        return art.file_data.read()
    except Exception:
        return None


def _upload_file_artifact(artifact_run, name: str, content: bytes, content_type: str = "application/octet-stream"):
    """Upload a file artifact to the given ArtifactRun."""
    from app.models.artifact import Artifact
    art = Artifact(
        run=artifact_run,
        name=name,
        artifact_type="file",
        content_type=content_type,
        size_bytes=len(content),
    )
    art.file_data.put(io.BytesIO(content), content_type=content_type)
    art.save()
    return art


def _get_option(key: str, default: str = "") -> str:
    from app.models.option import Option
    opt = Option.objects(key=key).first()
    return opt.value if opt else default


def _resolve_path_tokens(path: str, run, node_label: str = "") -> str:
    """Replace {date}, {datetime}, {workflow_name}, etc. in a remote path."""
    now = datetime.datetime.utcnow()
    pad = lambda n: str(n).zfill(2)
    wf_name = ""
    try:
        wf_name = run.workflow.name
    except Exception:
        pass
    ctx = {
        "date":            f"{now.year}-{pad(now.month)}-{pad(now.day)}",
        "datetime":        f"{now.year}-{pad(now.month)}-{pad(now.day)}T{pad(now.hour)}-{pad(now.minute)}-{pad(now.second)}",
        "year":            str(now.year),
        "month":           pad(now.month),
        "day":             pad(now.day),
        "workflow_run_id": str(run.id),
        "workflow_name":   wf_name,
        "node_name":       node_label,
    }
    import re
    return re.sub(r"\{(\w+)\}", lambda m: ctx.get(m.group(1), m.group(0)), path)


def _resolve_credential_env(credential) -> dict:
    """Resolve a credential's injectors and return a flat {ENV_VAR: value} dict.

    Mirrors the logic in apply_credentials.py so action nodes get the same
    injected variables that subprocesses see.
    """
    from app.services.crypto import decrypt
    import re
    _tmpl = re.compile(r"\{\{\s*(\w+)\s*\}\}")

    def _render(template: str, vals: dict) -> str:
        return _tmpl.sub(lambda m: str(vals.get(m.group(1), "")), template)

    try:
        raw = decrypt(credential.inputs) if credential.inputs else "{}"
        values: dict = json.loads(raw)
    except Exception:
        return {}

    try:
        injectors: dict = json.loads(credential.credential_type.injectors or "{}")
    except Exception:
        return {}

    result: dict = {}
    for env_key, tmpl in (injectors.get("env") or {}).items():
        result[env_key] = _render(str(tmpl), values)
    for var_key, tmpl in (injectors.get("extra_vars") or {}).items():
        result[var_key] = _render(str(tmpl), values)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 1. List Generator  →  JSON artifact (list of dicts)  →  CSV file artifact
# ─────────────────────────────────────────────────────────────────────────────

def execute_list_generator(cfg: dict, run) -> None:
    """Convert a JSON list-of-objects artifact to CSV or XLSX."""
    ar = _artifact_run(run)
    if not ar:
        raise RuntimeError("list_generator: workflow has no artifact cache configured")

    source_name = (cfg.get("source_artifact_tag") or cfg.get("source_artifact") or "").strip()
    fmt         = (cfg.get("format") or "csv").lower()
    output_name = (cfg.get("output_filename") or cfg.get("output_name") or "").strip()

    if not output_name:
        output_name = f"output.{fmt}"

    if not source_name:
        raise RuntimeError("list_generator: source_artifact_tag not configured")

    data = _read_json_artifact(ar, source_name)
    if data is None:
        raise RuntimeError(f"list_generator: artifact '{source_name}' not found or empty")
    if not isinstance(data, list):
        raise RuntimeError("list_generator: source artifact must be a JSON array of objects")

    # Collect columns from first row if not specified
    columns: list[str] = cfg.get("columns") or []
    if not columns and data:
        first = data[0] if isinstance(data[0], dict) else {}
        columns = list(first.keys())

    if fmt == "xlsx":
        content, content_type = _to_xlsx(data, columns)
    else:
        content, content_type = _to_csv(data, columns)

    _upload_file_artifact(ar, output_name, content, content_type)
    log.info("list_generator: wrote %d rows as %s → '%s'", len(data), fmt.upper(), output_name)


def _to_csv(data: list, columns: list[str]) -> tuple[bytes, str]:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in data:
        if isinstance(row, dict):
            writer.writerow(row)
    return buf.getvalue().encode("utf-8"), "text/csv"


def _cell_value(v):
    """Coerce a value to an Excel-safe type (str/int/float/bool/None)."""
    if v is None or isinstance(v, (int, float, bool)):
        return v
    if isinstance(v, str):
        return v
    # lists, dicts, and other complex types → JSON string
    return json.dumps(v, ensure_ascii=False)


def _to_xlsx(data: list, columns: list[str]) -> tuple[bytes, str]:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(columns)
    for row in data:
        if isinstance(row, dict):
            ws.append([_cell_value(row.get(col, "")) for col in columns])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ─────────────────────────────────────────────────────────────────────────────
# 2. PDF Generator  →  HTML template + JSON data  →  rendered file artifact
# ─────────────────────────────────────────────────────────────────────────────

def execute_pdf_generator(cfg: dict, run) -> None:
    """Render a Jinja2 HTML template with JSON data and store the result."""
    ar = _artifact_run(run)
    if not ar:
        raise RuntimeError("pdf_generator: workflow has no artifact cache configured")

    tmpl_name   = (cfg.get("template_artifact") or cfg.get("source_artifact_tag") or "").strip()
    data_name   = cfg.get("data_artifact", "").strip()
    output_name = (cfg.get("output_filename") or cfg.get("output_name") or "output.pdf").strip() or "output.pdf"

    if not tmpl_name:
        raise RuntimeError("pdf_generator: source artifact not configured")

    tmpl_bytes = _read_file_artifact(ar, tmpl_name)
    if tmpl_bytes is None:
        raise RuntimeError(f"pdf_generator: template artifact '{tmpl_name}' not found")

    context: dict = {}
    if data_name:
        data = _read_json_artifact(ar, data_name)
        if isinstance(data, dict):
            context = data
        elif isinstance(data, list):
            context = {"items": data}

    raw_text = tmpl_bytes.decode("utf-8", errors="replace")

    # Jinja2 templating (only when a data artifact is provided)
    if context:
        try:
            from jinja2 import Environment
            env = Environment(autoescape=False)
            raw_text = env.from_string(raw_text).render(**context)
        except Exception as exc:
            raise RuntimeError(f"pdf_generator: template rendering failed: {exc}") from exc

    # Markdown → HTML conversion when source is a .md / .markdown file
    is_markdown = tmpl_name.lower().endswith((".md", ".markdown"))
    if is_markdown:
        try:
            import markdown as md_lib
            html_body = md_lib.markdown(raw_text, extensions=["tables", "fenced_code", "nl2br"])
        except ImportError:
            html_body = f"<pre>{raw_text}</pre>"
        rendered_html = (
            "<!DOCTYPE html><html><head>"
            "<meta charset='utf-8'>"
            "<style>"
            "@page{size:A4 portrait;margin:2cm}"
            "html,body{width:100%;margin:0;padding:0;box-sizing:border-box}"
            "body{font-family:sans-serif;line-height:1.6;font-size:11pt}"
            "h1,h2,h3,h4{margin-top:1em;margin-bottom:0.4em}"
            "p{margin:0.5em 0}"
            "pre{background:#f4f4f4;padding:0.6em 0.8em;border-radius:3px;overflow-x:auto;font-size:9pt}"
            "code{background:#f4f4f4;padding:1px 4px;border-radius:2px;font-size:9pt}"
            "pre code{background:none;padding:0}"
            "table{border-collapse:collapse;width:100%;margin:0.5em 0}"
            "th,td{border:1px solid #ccc;padding:5px 8px;text-align:left}"
            "th{background:#f0f0f0;font-weight:bold}"
            "img{max-width:100%}"
            "</style></head>"
            f"<body>{html_body}</body></html>"
        )
    else:
        rendered_html = raw_text

    # WeasyPrint → PDF
    try:
        import weasyprint  # type: ignore
        pdf_bytes = weasyprint.HTML(string=rendered_html).write_pdf()
        content_type = "application/pdf"
        final_name = output_name
        log.info("pdf_generator: rendered PDF via weasyprint → '%s'", final_name)
    except ImportError:
        pdf_bytes = rendered_html.encode("utf-8")
        content_type = "text/html"
        final_name = output_name.replace(".pdf", ".html") if output_name.endswith(".pdf") else output_name + ".html"
        log.warning("pdf_generator: weasyprint not installed — saving rendered HTML as '%s'", final_name)

    _upload_file_artifact(ar, final_name, pdf_bytes, content_type)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Send Mail  →  email via SMTP (uses global SMTP settings from Options)
# ─────────────────────────────────────────────────────────────────────────────

def execute_send_mail(cfg: dict, run) -> None:
    """Send an email using the SMTP settings configured in global Settings."""
    from email.mime.base import MIMEBase
    from email import encoders

    to_list: list[str] = cfg.get("to") or []
    if isinstance(to_list, str):
        to_list = [a.strip() for a in to_list.split(",") if a.strip()]
    subject: str = (cfg.get("subject") or "").strip() or "Oachkatzl workflow notification"

    if not to_list:
        raise RuntimeError("send_mail: no recipients configured")

    smtp_host = _get_option("SMTP_HOST")
    if not smtp_host:
        raise RuntimeError("send_mail: SMTP_HOST not configured in global Settings")

    smtp_port = int(_get_option("SMTP_PORT", "587"))
    smtp_user = _get_option("SMTP_USER")
    smtp_pass = _get_option("SMTP_PASSWORD")
    smtp_from = _get_option("SMTP_FROM") or smtp_user or "oachkatzl@localhost"
    use_tls   = _get_option("SMTP_TLS", "true").lower() != "false"

    # Body — cfg.body is the static text field from the modal
    body_text: str = (cfg.get("body") or cfg.get("body_text") or "").strip()
    if not body_text:
        wf_name = ""
        try:
            wf_name = run.workflow.name
        except Exception:
            pass
        body_text = f"Workflow run '{wf_name}' — run ID: {run.id}"

    # Optional attachment from artifact cache
    attachment_name = (cfg.get("attachment_artifact_tag") or "").strip()
    attachment_bytes: bytes | None = None
    if attachment_name:
        ar = _artifact_run(run)
        if ar:
            attachment_bytes = _read_file_artifact(ar, attachment_name)
            if attachment_bytes is None:
                log.warning("send_mail: attachment artifact '%s' not found — sending without attachment", attachment_name)

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        if use_tls:
            smtp.starttls()
        if smtp_user:
            smtp.login(smtp_user, smtp_pass)

        for addr in to_list:
            if attachment_bytes is not None:
                msg: MIMEMultipart = MIMEMultipart("mixed")
                alt = MIMEMultipart("alternative")
                alt.attach(MIMEText(body_text, "plain", "utf-8"))
                msg.attach(alt)

                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_bytes)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=attachment_name)
                msg.attach(part)
            else:
                msg = MIMEMultipart("alternative")  # type: ignore[assignment]
                msg.attach(MIMEText(body_text, "plain", "utf-8"))

            msg["Subject"] = subject
            msg["From"]    = smtp_from
            msg["To"]      = addr
            smtp.send_message(msg)
            log.info("send_mail: sent to %s%s", addr,
                     f" with attachment '{attachment_name}'" if attachment_bytes else "")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Transfer File  →  SFTP/SMB/local via paramiko
# ─────────────────────────────────────────────────────────────────────────────

def execute_transfer_file(cfg: dict, run, node) -> None:
    """Transfer a file artifact to a remote host via SFTP/SMB or local copy."""
    ar = _artifact_run(run)
    if not ar:
        raise RuntimeError("transfer_file: workflow has no artifact cache configured")

    source_tag  = (cfg.get("source_artifact_tag") or "").strip()
    protocol    = (cfg.get("protocol") or "sftp").lower()
    remote_path = (cfg.get("remote_path") or "").strip()
    credential_id = (cfg.get("credential_id") or "").strip()

    if not source_tag:
        raise RuntimeError("transfer_file: source_artifact_tag not configured")
    if not remote_path:
        raise RuntimeError("transfer_file: remote_path not configured")

    node_label = getattr(node, "label", "") or ""
    remote_path = _resolve_path_tokens(remote_path, run, node_label)

    # Read source artifact
    file_bytes = _read_file_artifact(ar, source_tag)
    if file_bytes is None:
        raise RuntimeError(f"transfer_file: artifact '{source_tag}' not found in run")

    # Resolve credential injectors → flat {ENV_VAR: value} dict
    cred_env: dict = {}
    if credential_id:
        try:
            from app.models.credential import Credential
            cred_obj = Credential.objects(id=credential_id).first()
            if cred_obj:
                cred_env = _resolve_credential_env(cred_obj)
        except Exception as exc:
            log.warning("transfer_file: could not resolve credential %s: %s", credential_id, exc)

    if protocol == "local":
        _transfer_local(file_bytes, source_tag, remote_path)
    elif protocol in ("sftp", "scp"):
        _transfer_sftp(file_bytes, source_tag, remote_path, cred_env)
    elif protocol == "smb":
        _transfer_smb(file_bytes, source_tag, remote_path, cred_env)
    else:
        raise RuntimeError(f"transfer_file: unknown protocol '{protocol}'")


def _transfer_local(file_bytes: bytes, filename: str, remote_path: str) -> None:
    import os
    dest = remote_path
    if dest.endswith("/") or dest.endswith(os.sep):
        os.makedirs(dest, exist_ok=True)
        dest = os.path.join(dest, filename)
    else:
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "wb") as fh:
        fh.write(file_bytes)
    log.info("transfer_file (local): wrote %d bytes → %s", len(file_bytes), dest)


def _transfer_sftp(file_bytes: bytes, filename: str, remote_path: str, cred_env: dict) -> None:
    import paramiko  # type: ignore

    host = (cred_env.get("SFTP_HOST") or "").strip()
    port = int(cred_env.get("SFTP_PORT") or 22)
    user = (cred_env.get("SFTP_USERNAME") or "").strip()

    if not host:
        raise RuntimeError("transfer_file (sftp): SFTP_HOST not set in credential injectors")

    transport = paramiko.Transport((host, port))
    try:
        private_key_str = cred_env.get("SFTP_KEY") or ""
        password        = cred_env.get("SFTP_PASSWORD") or ""

        if private_key_str:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False) as tmp:
                tmp.write(private_key_str)
                key_path = tmp.name
            try:
                pkey = paramiko.RSAKey.from_private_key_file(key_path, password=password or None)
            except paramiko.SSHException:
                pkey = paramiko.Ed25519Key.from_private_key_file(key_path, password=password or None)
            finally:
                import os; os.unlink(key_path)
            transport.connect(username=user, pkey=pkey)
        elif password:
            transport.connect(username=user, password=password)
        else:
            raise RuntimeError("transfer_file (sftp): no SSH key or password in credential")

        sftp = paramiko.SFTPClient.from_transport(transport)
        dest = remote_path
        if dest.endswith("/"):
            dest = dest + filename
        # mkdir -p: create each missing directory component
        remote_dir = dest.rsplit("/", 1)[0] if "/" in dest else ""
        if remote_dir:
            prefix  = "/" if remote_dir.startswith("/") else ""
            current = prefix
            for part in remote_dir.lstrip("/").split("/"):
                if not part:
                    continue
                current = current.rstrip("/") + "/" + part
                try:
                    sftp.stat(current)
                except OSError:
                    sftp.mkdir(current)

        with sftp.open(dest, "wb") as fh:
            fh.write(file_bytes)
        log.info("transfer_file (sftp): uploaded %d bytes → %s@%s:%s", len(file_bytes), user, host, dest)
    finally:
        transport.close()


def _transfer_smb(file_bytes: bytes, filename: str, remote_path: str, cred_env: dict) -> None:
    try:
        from smbprotocol.connection import Connection  # type: ignore
        from smbprotocol.open import Open, CreateDisposition, CreateOptions, FileAttributes, FilePipePrinterAccessMask, ImpersonationLevel  # type: ignore
        from smbprotocol.session import Session  # type: ignore
        from smbprotocol.tree import TreeConnect  # type: ignore
    except ImportError:
        raise RuntimeError("transfer_file (smb): smbprotocol package not installed in worker image")

    host     = (cred_env.get("SMB_HOST") or "").strip()
    user     = (cred_env.get("SMB_USERNAME") or "").strip()
    password = cred_env.get("SMB_PASSWORD") or ""
    domain   = cred_env.get("SMB_DOMAIN") or ""
    share    = (cred_env.get("SMB_SHARE") or "").strip()

    if not host:
        raise RuntimeError("transfer_file (smb): SMB_HOST not set in credential injectors")
    if not user or not password:
        raise RuntimeError(
            "transfer_file (smb): SMB_USERNAME and SMB_PASSWORD must be set — "
            "empty credentials cause guest authentication which the server rejects"
        )

    # Share: from credential injector (SMB_SHARE) or first path component
    path = remote_path.replace("/", "\\").lstrip("\\")
    if share:
        file_path = "\\" + path.lstrip("\\") if path else "\\" + filename
    else:
        parts     = path.split("\\", 1)
        share     = parts[0]
        file_path = ("\\" + parts[1]) if len(parts) > 1 else "\\" + filename

    import uuid
    conn = Connection(uuid.uuid4(), host, 445, require_signing=False)
    conn.connect()
    try:
        smb_user = f"{domain}\\{user}" if domain and user else user
        session = Session(conn, smb_user, password)
        session.connect()
        tree = TreeConnect(session, f"\\\\{host}\\{share}")
        tree.connect()

        # mkdir -p: create each directory component if missing
        remote_dir = file_path.rsplit("\\", 1)[0] if "\\" in file_path.lstrip("\\") else ""
        if remote_dir:
            current = ""
            for part in remote_dir.strip("\\").split("\\"):
                if not part:
                    continue
                current = current + "\\" + part
                dir_fh = Open(tree, current.lstrip("\\"))
                try:
                    dir_fh.create(
                        impersonation_level=ImpersonationLevel.Impersonation,
                        desired_access=FilePipePrinterAccessMask.GENERIC_READ,
                        file_attributes=FileAttributes.FILE_ATTRIBUTE_DIRECTORY,
                        share_access=0,
                        create_disposition=CreateDisposition.FILE_OPEN_IF,
                        create_options=CreateOptions.FILE_DIRECTORY_FILE,
                    )
                    dir_fh.close()
                except Exception as exc:
                    log.debug("transfer_file (smb): mkdir %s: %s", current, exc)

        fh = Open(tree, file_path.lstrip("\\"))
        fh.create(
            impersonation_level=ImpersonationLevel.Impersonation,
            desired_access=FilePipePrinterAccessMask.GENERIC_WRITE,
            file_attributes=FileAttributes.FILE_ATTRIBUTE_NORMAL,
            share_access=0,
            create_disposition=CreateDisposition.FILE_OVERWRITE_IF,
            create_options=CreateOptions.FILE_NON_DIRECTORY_FILE,
        )
        fh.write(file_bytes, 0)
        fh.close()
        log.info("transfer_file (smb): uploaded %d bytes → \\\\%s\\%s%s", len(file_bytes), host, share, file_path)
    finally:
        try:
            conn.disconnect()
        except Exception:
            pass  # suppress cleanup errors so the real exception propagates
