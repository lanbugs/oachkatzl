from __future__ import annotations

import json
import os
import re
import stat
import tempfile


_TMPL_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def _render(template_str: str, values: dict) -> str:
    return _TMPL_RE.sub(lambda m: str(values.get(m.group(1), "")), template_str)


def apply_credentials(task) -> tuple[dict, dict, list[str]]:
    """Resolve all credentials attached to the task's template.

    Returns:
        env_additions   — dict to merge into the process environment
        extra_var_additions — dict to merge into Ansible extra-vars
        cleanup         — list of temp file paths to delete after the task
    """
    from app.services.crypto import decrypt

    env_additions: dict = {}
    extra_var_additions: dict = {}
    cleanup: list[str] = []

    credentials = getattr(task.template, "credentials", []) or []

    for cred in credentials:
        if not cred:
            continue
        try:
            raw = decrypt(cred.inputs) if cred.inputs else "{}"
            values: dict = json.loads(raw)
        except Exception:
            continue

        try:
            injectors: dict = json.loads(cred.credential_type.injectors or "{}")
        except Exception:
            continue

        # env section
        for env_key, tmpl in (injectors.get("env") or {}).items():
            env_additions[env_key] = _render(str(tmpl), values)

        # extra_vars section
        for var_key, tmpl in (injectors.get("extra_vars") or {}).items():
            rendered = _render(str(tmpl), values)
            extra_var_additions[var_key] = rendered
            env_additions[var_key] = rendered   # also expose as env var for bash/python

        # file section
        file_cfg = injectors.get("file")
        if file_cfg and isinstance(file_cfg, dict):
            content = _render(str(file_cfg.get("content", "")), values)
            var_name = str(file_cfg.get("var", ""))
            if content and var_name:
                fd, path = tempfile.mkstemp()
                os.close(fd)
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
                with open(path, "w") as f:
                    f.write(content)
                cleanup.append(path)
                env_additions[var_name] = path

    return env_additions, extra_var_additions, cleanup
