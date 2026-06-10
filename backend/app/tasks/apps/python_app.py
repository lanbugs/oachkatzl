from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Callable


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


def venv_install(
    workdir: str,
    env: dict,
    on_line: Callable[[str], None],
    debug: bool = False,
) -> str:
    """Create an isolated .venv and install requirements.txt if present.

    Returns the path to the venv Python interpreter so build_command can use it.
    Falls back to the system Python if no requirements.txt is found.
    """
    req_path  = os.path.join(workdir, "requirements.txt")
    venv_path = os.path.join(workdir, ".venv")
    venv_python = os.path.join(venv_path, "bin", "python")
    venv_pip    = os.path.join(venv_path, "bin", "pip")

    if not os.path.isfile(req_path):
        on_line("[venv] No requirements.txt found — skipping venv creation")
        return sys.executable

    on_line("[venv] Found requirements.txt — creating virtual environment …")

    # Create venv
    result = subprocess.run(
        [sys.executable, "-m", "venv", venv_path],
        capture_output=True, text=True, cwd=workdir, env=env,
    )
    for line in (result.stdout + result.stderr).splitlines():
        if line.strip():
            on_line(f"[venv] {line}")

    if result.returncode != 0:
        on_line(f"[venv] ERROR: venv creation failed (exit {result.returncode}) — falling back to system Python")
        return sys.executable

    on_line(f"[venv] Virtual environment created at {venv_path}")

    # pip install -r requirements.txt
    on_line("[venv] Installing requirements.txt …")
    if debug:
        on_line(f"[venv] Running: {venv_pip} install -r {req_path}")

    # Upgrade pip first (silent) so we don't get noisy deprecation warnings
    subprocess.run(
        [venv_pip, "install", "--quiet", "--upgrade", "pip"],
        capture_output=True, cwd=workdir, env=env,
    )

    result = subprocess.run(
        [venv_pip, "install", "-r", req_path],
        capture_output=True, text=True, cwd=workdir, env=env,
    )
    for line in result.stdout.splitlines():
        on_line(f"[venv] {line}")
    for line in result.stderr.splitlines():
        if line.strip():
            on_line(f"[venv] {line}")

    if result.returncode == 0:
        on_line("[venv] Requirements installed successfully.")
    else:
        on_line(f"[venv] WARNING: pip install exited with code {result.returncode}")

    return venv_python


def build_command(
    task,
    workdir: str,
    python_executable: str | None = None,
) -> tuple[list[str], list[str]]:
    template = task.template
    script   = _safe_script_path(workdir, template.playbook, "main.py")
    interp   = python_executable or sys.executable

    cmd = [interp, script]

    try:
        use_override = template.allow_override_args and task.arguments_override not in (None, "[]", "")
        args = json.loads(task.arguments_override if use_override else (template.arguments or "[]"))
        cmd.extend(str(a) for a in args)
    except json.JSONDecodeError:
        pass

    return cmd, []
