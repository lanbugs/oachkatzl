from __future__ import annotations

import os
import shutil
import stat
import tempfile

from app.config import settings


def _normalize_key(raw: str) -> str:
    """Ensure the private key has real newlines and a trailing newline.

    Keys stored via JSON or pasted into a textarea often arrive with literal
    backslash-n sequences instead of actual newline characters.
    """
    # Replace JSON-escaped newlines
    key = raw.replace("\\n", "\n")
    # Normalize Windows line endings
    key = key.replace("\r\n", "\n").replace("\r", "\n")
    key = key.strip()
    if key and not key.endswith("\n"):
        key += "\n"
    return key


def _key_file(private_key_pem: str, passphrase: str = "") -> str:
    """Write private key to a secure temp file.

    If a passphrase is provided, ssh-keygen strips it in-place so that SSH
    can use the key with BatchMode=yes. ssh-keygen handles every key format
    (OpenSSH, RSA, ECDSA, Ed25519) reliably.
    """
    import subprocess

    key = _normalize_key(private_key_pem)
    passphrase = passphrase.strip()

    fd, path = tempfile.mkstemp(prefix="oachkatzl_key_")
    os.close(fd)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    with open(path, "w") as f:
        f.write(key)

    if passphrase:
        # Strip passphrase: rewrite key without passphrase so BatchMode works.
        # ssh-keygen -p -P <old> -N '' -f <file>  (modifies file in-place)
        result = subprocess.run(
            ["ssh-keygen", "-p", "-P", passphrase, "-N", "", "-f", path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            os.unlink(path)
            raise RuntimeError(
                "Could not decrypt SSH key — wrong passphrase or unsupported key format. "
                f"ssh-keygen said: {result.stderr.strip()}"
            )

    return path


def clone_or_update(
    repo, workdir: str, debug: bool = False, on_line=None
) -> str:
    """Clone or update repository into workdir. Returns HEAD commit hash."""
    import git as gitpython

    def log(msg: str) -> None:
        if debug and on_line:
            on_line(f"[git] {msg}")

    url = repo.git_url
    branch = repo.git_branch or "main"
    key_path = None

    # Minimal env — never pass worker secrets to git subprocess
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/root"),
        "GIT_TERMINAL_PROMPT": "0",
    }

    if repo.ssh_key and repo.ssh_key.type == "ssh":
        from app.services.crypto import decrypt
        import json

        log(f"Using SSH key '{repo.ssh_key.name}'")
        secret_raw = decrypt(repo.ssh_key.secret)
        secret = json.loads(secret_raw) if secret_raw else {}
        private_key = secret.get("private_key", "")
        passphrase = secret.get("passphrase", "")
        if private_key:
            key_path = _key_file(private_key, passphrase)
            ssh_cmd = (
                f"ssh -i {key_path}"
                f" -o StrictHostKeyChecking=no"
                f" -o IdentitiesOnly=yes"
                f" -o BatchMode=yes"
            )
            env["GIT_SSH_COMMAND"] = ssh_cmd
            log(f"SSH command: {ssh_cmd}")

    try:
        if os.path.exists(os.path.join(workdir, ".git")):
            log(f"Updating existing clone in {workdir}")
            repo_obj = gitpython.Repo(workdir)
            with repo_obj.git.custom_environment(GIT_SSH_COMMAND=env.get("GIT_SSH_COMMAND", "")):
                repo_obj.remotes.origin.fetch()
            repo_obj.git.checkout(branch)
            repo_obj.git.reset("--hard", f"origin/{branch}")
        else:
            log(f"Cloning {url}  branch={branch}  →  {workdir}")
            os.makedirs(workdir, exist_ok=True)
            repo_obj = gitpython.Repo.clone_from(url, workdir, branch=branch, env=env)

        commit = repo_obj.head.commit
        log(f"HEAD {commit.hexsha[:8]} — {commit.summary}")
        return commit.hexsha
    finally:
        if key_path and os.path.exists(key_path):
            os.unlink(key_path)


def cleanup_workdir(workdir: str) -> None:
    if os.path.exists(workdir):
        shutil.rmtree(workdir, ignore_errors=True)
