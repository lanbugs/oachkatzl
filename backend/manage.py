"""Management commands — runs without gevent, before gunicorn starts."""
from __future__ import annotations

import os
import secrets
import sys
import mongoengine


def bootstrap() -> None:
    from app.config import settings

    mongoengine.connect(host=settings.MONGO_URI)

    # ── Admin user ────────────────────────────────────────────────────────
    from app.models.user import User
    from app.services.auth_service import hash_password

    if not User.objects(is_admin=True).first():
        explicit_password = os.environ.get("OACHKATZL_ADMIN_PASSWORD", "")
        if not explicit_password or explicit_password == "changeme":
            admin_password = secrets.token_urlsafe(16)
            print(f"[bootstrap] Generated admin password: {admin_password}", flush=True)
            print("[bootstrap] ** SAVE THIS — it will not be shown again! **", flush=True)
        else:
            admin_password = explicit_password

        User(
            username=settings.ADMIN_USER,
            email=settings.ADMIN_EMAIL,
            name="Administrator",
            password_hash=hash_password(admin_password),
            is_admin=True,
            active=True,
        ).save()
        print(f"[bootstrap] Admin user '{settings.ADMIN_USER}' created.", flush=True)
    else:
        print("[bootstrap] Admin user already exists.", flush=True)

    # ── SMTP settings from env (only if not already configured) ──────────
    from app.models.option import Option
    from app.services.crypto import encrypt

    _SENSITIVE_SMTP_KEYS = {"SMTP_PASSWORD"}

    smtp_keys = {
        "SMTP_HOST":     os.getenv("SMTP_HOST", ""),
        "SMTP_PORT":     os.getenv("SMTP_PORT", "587"),
        "SMTP_TLS":      os.getenv("SMTP_TLS", "true"),
        "SMTP_USER":     os.getenv("SMTP_USER", ""),
        "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD", ""),
        "SMTP_FROM":     os.getenv("SMTP_FROM", ""),
    }

    for key, value in smtp_keys.items():
        if value and not Option.objects(key=key).first():
            store_value = encrypt(value) if key in _SENSITIVE_SMTP_KEYS else value
            Option(key=key, value=store_value).save()
            print(f"[bootstrap] Option {key} set from environment.", flush=True)

    mongoengine.disconnect_all()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "bootstrap"
    if cmd == "bootstrap":
        bootstrap()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
