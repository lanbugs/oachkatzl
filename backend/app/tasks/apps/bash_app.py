from __future__ import annotations

import json
import os
import shutil


def _safe_script_path(workdir: str, rel_path: str, default: str) -> str:
    """Resolve script path within workdir; raise ValueError for absolute paths or traversal."""
    path = rel_path or default
    if os.path.isabs(path):
        raise ValueError(f"Absolute script paths are not allowed: {path!r}")
    real_workdir = os.path.realpath(workdir)
    resolved = os.path.realpath(os.path.join(workdir, path))
    if not (resolved == real_workdir or resolved.startswith(real_workdir + os.sep)):
        raise ValueError(f"Script path escapes working directory: {path!r}")
    return resolved


def build_command(task, workdir: str) -> tuple[list[str], list[str]]:
    template = task.template
    script = _safe_script_path(workdir, template.playbook, "run.sh")
    # Prefer bash; fall back to sh (Alpine ships only sh by default)
    bash = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
    cmd = [bash, script]

    try:
        use_override = template.allow_override_args and task.arguments_override not in (None, "[]", "")
        args = json.loads(task.arguments_override if use_override else (template.arguments or "[]"))
        cmd.extend(str(a) for a in args)
    except json.JSONDecodeError:
        pass

    return cmd, []
