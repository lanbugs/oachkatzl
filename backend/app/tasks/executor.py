from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from typing import Callable


def _write_temp(content: str, suffix: str = "") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    with open(path, "w") as f:
        f.write(content)
    return path


# Variables from the worker process that are safe to inherit
_SAFE_INHERIT = {"PATH", "HOME", "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE",
                 "USER", "LOGNAME", "SHELL", "TERM", "TMPDIR", "TMP", "TEMP",
                 # SSH agent forwarding
                 "SSH_AUTH_SOCK", "SSH_AGENT_PID",
                 # Ansible
                 "ANSIBLE_FORCE_COLOR", "ANSIBLE_STDOUT_CALLBACK"}


def build_env(task, workdir: str) -> tuple[dict, list[str]]:
    """Build a minimal, filtered process environment for the subprocess.

    Only safe system variables are inherited. OACHKATZL_* secrets (passwords,
    JWT secret, encryption key, …) are explicitly excluded so they never
    leak into playbooks or scripts.
    """
    # Start from a curated subset of the current environment
    base_env: dict[str, str] = {
        k: v for k, v in os.environ.items() if k in _SAFE_INHERIT
    }

    # Ensure a minimal PATH is always present
    base_env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
    base_env.setdefault("HOME", "/root")

    # Nice defaults for Ansible output
    base_env.setdefault("ANSIBLE_FORCE_COLOR", "1")
    base_env.setdefault("ANSIBLE_HOST_KEY_CHECKING", "False")

    template = task.template

    # Env-vars from the Environment model (user-defined)
    if template.environment:
        # Process env vars (e.g. AWS_REGION, KUBECONFIG, …)
        try:
            env_vars = json.loads(template.environment.env or "{}")
            base_env.update({k: str(v) for k, v in env_vars.items()})
        except json.JSONDecodeError:
            pass

        # Extra-vars / variables (JSON dict → also injected as env vars for
        # bash/python; Ansible additionally gets them via --extra-vars)
        try:
            extra_vars = json.loads(template.environment.json or "{}")
            base_env.update({k: str(v) for k, v in extra_vars.items()})
        except json.JSONDecodeError:
            pass

    # Per-task environment override
    try:
        overrides = json.loads(task.environment_override or "{}")
        base_env.update({k: str(v) for k, v in overrides.items()})
    except json.JSONDecodeError:
        pass

    # Survey answers → env vars (highest priority, override everything above)
    # e.g. survey var "deploy_env" → $deploy_env in bash, os.environ["deploy_env"] in python
    try:
        survey = json.loads(task.survey_answers or "{}")
        base_env.update({k: ("true" if v is True else "false" if v is False else str(v)) for k, v in survey.items() if k})
    except json.JSONDecodeError:
        pass

    # Task metadata (harmless, always available)
    base_env["OACHKATZL_TASK_ID"] = str(task.id)
    base_env["OACHKATZL_WORKDIR"] = workdir

    # Version — set for build tasks (the version being built) and
    # deploy tasks (the version being deployed). Use as $OACHKATZL_BUILD_VERSION
    if task.version:
        base_env["OACHKATZL_BUILD_VERSION"] = task.version

    # For deploy tasks: the source build task ID
    if task.build_task:
        base_env["OACHKATZL_BUILD_TASK_ID"] = str(task.build_task.id)

    return base_env, []


def run_command(
    cmd: list[str],
    env: dict,
    workdir: str,
    on_line: Callable[[str], None],
    stop_flag: Callable[[], bool],
    stop_check_interval: float = 0.5,
) -> int:
    """Run a subprocess and stream its output line by line.

    The stop flag is checked every *stop_check_interval* seconds in a
    dedicated watcher thread — completely independent of whether the
    process is producing output. This ensures that long-running silent
    tasks (e.g. Ansible waiting for an SSH connection) can be stopped
    immediately without waiting for the next output line.
    """
    import threading

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=workdir,
        env=env,
        text=True,
        bufsize=1,
    )

    _proc_done = threading.Event()

    def _watcher() -> None:
        """Poll stop_flag every interval; kill the process when set."""
        while not _proc_done.wait(timeout=stop_check_interval):
            if stop_flag():
                if proc.poll() is None:          # process still running
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)    # give SIGTERM 10 s
                    except subprocess.TimeoutExpired:
                        proc.kill()              # escalate to SIGKILL
                return                           # watcher's job is done

    watcher = threading.Thread(target=_watcher, daemon=True)
    watcher.start()

    try:
        for line in proc.stdout:
            on_line(line.rstrip("\n"))
        proc.wait()
    except Exception:
        proc.kill()
        raise
    finally:
        _proc_done.set()     # tell the watcher the process is finished
        watcher.join(timeout=2)

    return proc.returncode
