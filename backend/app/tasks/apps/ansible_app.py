from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from typing import Callable

from app.services.crypto import decrypt


def _validate_relative_path(workdir: str, rel_path: str) -> str:
    """Validate that rel_path stays within workdir; raise ValueError otherwise."""
    if not rel_path:
        return rel_path
    if os.path.isabs(rel_path):
        raise ValueError(f"Absolute paths are not allowed: {rel_path!r}")
    real_workdir = os.path.realpath(workdir)
    resolved = os.path.realpath(os.path.join(workdir, rel_path))
    if not (resolved == real_workdir or resolved.startswith(real_workdir + os.sep)):
        raise ValueError(f"Path escapes working directory: {rel_path!r}")
    return rel_path


# Requirements files checked relative to the workdir root.
# Each tuple: (relative_path, galaxy_subcommand)
#   galaxy_subcommand is "role" or "collection"
_REQUIREMENTS_CHECKS = [
    # Root requirements.yml may contain both roles and collections
    ("requirements.yml",             "role"),
    ("requirements.yml",             "collection"),
    # Dedicated roles file
    ("roles/requirements.yml",       "role"),
    # Dedicated collections file
    ("collections/requirements.yml", "collection"),
]


def galaxy_install(
    workdir: str,
    env: dict,
    on_line: Callable[[str], None],
    debug: bool = False,
) -> None:
    """Check for Galaxy requirements files and install roles/collections.

    - requirements.yml             → ansible-galaxy role install + collection install
    - roles/requirements.yml       → ansible-galaxy role install
    - collections/requirements.yml → ansible-galaxy collection install

    Roles are installed into ``{workdir}/.galaxy/roles`` and collections into
    ``{workdir}/.galaxy/collections`` so that concurrent tasks are isolated.
    The caller must set ANSIBLE_ROLES_PATH / ANSIBLE_COLLECTIONS_PATHS in env.
    """
    roles_path       = os.path.join(workdir, ".galaxy", "roles")
    collections_path = os.path.join(workdir, ".galaxy", "collections")
    os.makedirs(roles_path,       exist_ok=True)
    os.makedirs(collections_path, exist_ok=True)

    # Track (file, subcommand) pairs already processed to avoid duplicates
    done: set[tuple[str, str]] = set()

    for rel_path, subcmd in _REQUIREMENTS_CHECKS:
        abs_path = os.path.join(workdir, rel_path)

        if not os.path.isfile(abs_path):
            on_line(f"[galaxy] No {rel_path} found — skipping {subcmd} install")
            continue

        key = (abs_path, subcmd)
        if key in done:
            continue
        done.add(key)

        on_line(f"[galaxy] Found {rel_path} — installing {subcmd}s …")

        if subcmd == "role":
            cmd = [
                "ansible-galaxy", "role", "install",
                "-r", abs_path,
                "-p", roles_path,
            ]
        else:
            cmd = [
                "ansible-galaxy", "collection", "install",
                "-r", abs_path,
                "-p", collections_path,
            ]

        if debug:
            on_line(f"[galaxy] Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=workdir,
            env=env,
        )

        for line in result.stdout.splitlines():
            on_line(f"[galaxy] {line}")
        for line in result.stderr.splitlines():
            on_line(f"[galaxy] {line}")

        if result.returncode == 0:
            on_line(f"[galaxy] {subcmd} install completed.")
        else:
            on_line(
                f"[galaxy] WARNING: ansible-galaxy {subcmd} install "
                f"exited with code {result.returncode}"
            )


def build_command(task, workdir: str) -> tuple[list[str], list[str]]:
    """Return (cmd, temp_files_to_cleanup)."""
    template = task.template
    cleanup = []

    playbook = _validate_relative_path(workdir, template.playbook or "site.yml")
    cmd = ["ansible-playbook", playbook]

    # Inventory
    if template.inventory:
        inv = template.inventory
        if inv.type in ("static", "static-yaml"):
            suffix = ".yml" if inv.type == "static-yaml" else ".ini"
            fd, inv_path = tempfile.mkstemp(suffix=suffix)
            os.close(fd)
            os.chmod(inv_path, stat.S_IRUSR | stat.S_IWUSR)
            with open(inv_path, "w") as f:
                f.write(inv.inventory or "")
            cleanup.append(inv_path)
            cmd += ["-i", inv_path]
        elif inv.type == "file":
            inv_file = _validate_relative_path(workdir, inv.inventory_file or "hosts")
            cmd += ["-i", os.path.join(workdir, inv_file)]

    # Extra vars from environment
    extra_vars: dict = {}
    if template.environment:
        try:
            extra_vars.update(json.loads(template.environment.json or "{}"))
        except json.JSONDecodeError:
            pass

    # Survey answers
    try:
        survey = json.loads(task.survey_answers or "{}")
        extra_vars.update(survey)
    except json.JSONDecodeError:
        pass

    # Environment override
    try:
        env_override = json.loads(task.environment_override or "{}")
        extra_vars.update(env_override)
    except json.JSONDecodeError:
        pass

    if extra_vars:
        fd, ev_path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.chmod(ev_path, stat.S_IRUSR | stat.S_IWUSR)
        with open(ev_path, "w") as f:
            json.dump(extra_vars, f)
        cleanup.append(ev_path)
        cmd += ["--extra-vars", f"@{ev_path}"]

    # Vault passwords
    for vault_ref in template.vaults:
        if vault_ref.key:
            try:
                secret_raw = decrypt(vault_ref.key.secret)
                secret = json.loads(secret_raw)
                vault_pw = secret.get("vault_password", "")
                if vault_pw:
                    fd, vp_path = tempfile.mkstemp()
                    os.close(fd)
                    os.chmod(vp_path, stat.S_IRUSR | stat.S_IWUSR)
                    with open(vp_path, "w") as f:
                        f.write(vault_pw)
                    cleanup.append(vp_path)
                    cmd += [f"--vault-id={vault_ref.vault_id}@{vp_path}"]
            except Exception:
                pass

    # Become / SSH keys
    if template.inventory and template.inventory.ssh_key:
        try:
            sk_raw = decrypt(template.inventory.ssh_key.secret)
            sk = json.loads(sk_raw)
            pk = sk.get("private_key", "")
            if pk:
                fd, sk_path = tempfile.mkstemp()
                os.close(fd)
                os.chmod(sk_path, stat.S_IRUSR | stat.S_IWUSR)
                with open(sk_path, "w") as f:
                    f.write(pk)
                cleanup.append(sk_path)
                cmd += ["--private-key", sk_path]
        except Exception:
            pass

    # Flags
    if task.dry_run:
        cmd.append("--check")
    if task.diff:
        cmd.append("--diff")
    if task.debug:
        cmd.append("-vvvv")

    # Arguments (template + override)
    try:
        if template.allow_override_args and task.arguments_override not in (None, "[]", ""):
            args = json.loads(task.arguments_override or "[]")
        else:
            args = json.loads(template.arguments or "[]")
        cmd.extend(str(a) for a in args)
    except json.JSONDecodeError:
        pass

    return cmd, cleanup
