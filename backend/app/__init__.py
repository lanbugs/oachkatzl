from __future__ import annotations

from apiflask import APIFlask
from flask import jsonify

from app.config import settings


def create_app(config_overrides: dict | None = None) -> APIFlask:
    app = APIFlask(
        __name__,
        title="Oachkatzl API",
        version="1.0.0",
        spec_path="/api/openapi.json",
        docs_path="/api/docs",
    )
    app.url_map.strict_slashes = False

    app.config["SECRET_KEY"] = settings.JWT_SECRET
    app.config["OACHKATZL_SETTINGS"] = settings

    if config_overrides:
        app.config.update(config_overrides)

    if app.config.get("TESTING"):
        app.config["RATELIMIT_ENABLED"] = False
    else:
        settings.validate_production()
        from app.extensions import init_extensions
        init_extensions(app)
        _bootstrap_ldap()

    _register_blueprints(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    return app


def _bootstrap_ldap() -> None:
    """Seed LdapConfig from env vars on first boot (if not yet in DB)."""
    try:
        from app.config import settings
        from app.models.ldap_config import LdapConfig
        from app.services.crypto import encrypt
        if settings.LDAP_SERVER_URL and not LdapConfig.objects.first():
            LdapConfig(
                enabled              = True,
                server_url           = settings.LDAP_SERVER_URL,
                bind_dn              = settings.LDAP_BIND_DN,
                bind_password_enc    = encrypt(settings.LDAP_BIND_PASSWORD) if settings.LDAP_BIND_PASSWORD else "",
                base_dn              = settings.LDAP_BASE_DN,
                user_search_filter   = settings.LDAP_USER_FILTER,
            ).save()
    except Exception:
        pass   # don't crash startup if DB isn't ready yet


def _register_blueprints(app: APIFlask) -> None:
    from app.api.auth import bp as auth_bp
    from app.api.users import bp as users_bp
    from app.api.projects import bp as projects_bp
    from app.api.keys import bp as keys_bp
    from app.api.repositories import bp as repos_bp
    from app.api.inventories import bp as inv_bp
    from app.api.environments import bp as env_bp
    from app.api.templates import bp as tmpl_bp
    from app.api.tasks import bp as tasks_bp
    from app.api.schedules import bp as sched_bp
    from app.api.integrations import bp as integ_bp
    from app.api.views import bp as views_bp
    from app.api.custom_apps import bp as capps_bp
    from app.api.settings import bp as settings_bp
    from app.api.backup import bp as backup_bp
    from app.api.notifications import bp as notif_bp
    from app.api.template_tokens import bp as tokens_bp
    from app.api.ldap import bp as ldap_bp
    from app.api.credential_types import bp as cred_types_bp
    from app.api.credentials import bp as creds_bp
    from app.api.workflows import bp as workflows_bp

    for blueprint in (
        auth_bp, users_bp, projects_bp, keys_bp, repos_bp, inv_bp,
        env_bp, tmpl_bp, tasks_bp, sched_bp, integ_bp, views_bp,
        capps_bp, settings_bp, backup_bp, notif_bp, tokens_bp, ldap_bp,
        cred_types_bp, creds_bp, workflows_bp,
    ):
        app.register_blueprint(blueprint)


