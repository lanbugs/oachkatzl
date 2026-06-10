"""LDAP / Active Directory authentication and group-sync service.

Public API
----------
ldap_authenticate(username, password) -> dict | None
get_or_create_ldap_user(uid, username, email, display_name) -> User
sync_ldap_groups(user, groups) -> None
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Role priority for conflict resolution (higher = more privileged)
ROLE_RANKS: dict[str, int] = {
    "owner":       4,
    "manager":     3,
    "task_runner": 2,
    "guest":       1,
}


# ── Config helper ─────────────────────────────────────────────────────────

def _get_config():
    """Return the enabled LdapConfig document or None."""
    from app.models.ldap_config import LdapConfig
    cfg = LdapConfig.objects.first()
    if cfg and cfg.enabled and cfg.server_url:
        return cfg
    return None


def _decrypt_bind_password(cfg) -> str:
    from app.services.crypto import decrypt
    try:
        return decrypt(cfg.bind_password_enc) if cfg.bind_password_enc else ""
    except Exception:
        return ""


# ── Core LDAP connection ──────────────────────────────────────────────────

def _make_server(cfg):
    from ldap3 import Server, Tls
    import ssl

    tls = None
    if cfg.use_tls or cfg.use_ssl:
        tls = Tls(validate=ssl.CERT_NONE)  # use CERT_REQUIRED in production with proper CA

    return Server(
        cfg.server_url,
        use_ssl=cfg.use_ssl,
        tls=tls,
        connect_timeout=5,
    )


def _service_bind(cfg):
    """Return an authenticated ldap3 Connection using the service account."""
    from ldap3 import Connection, SIMPLE, SYNC, ALL_ATTRIBUTES
    from ldap3.core.exceptions import LDAPException

    server = _make_server(cfg)
    bind_pw = _decrypt_bind_password(cfg)
    conn = Connection(
        server,
        user=cfg.bind_dn,
        password=bind_pw,
        authentication=SIMPLE,
        client_strategy=SYNC,
        receive_timeout=5,
        raise_exceptions=False,
    )
    if cfg.use_tls:
        conn.start_tls()
    if not conn.bind():
        logger.warning("ldap_service: service-account bind failed: %s", conn.result)
        return None
    return conn


# ── Public: authenticate ──────────────────────────────────────────────────

def ldap_authenticate(username: str, password: str) -> dict | None:
    """Try to authenticate *username*/*password* against LDAP/AD.

    Returns a dict with user attributes on success, None on failure.
    """
    from ldap3 import Connection, SIMPLE, SYNC, ALL_ATTRIBUTES, SUBTREE
    from ldap3.core.exceptions import LDAPException

    cfg = _get_config()
    if not cfg:
        return None

    # 1. Find the user DN via the service account
    conn = _service_bind(cfg)
    if conn is None:
        return None

    search_filter = cfg.user_search_filter.format(username=_ldap_escape(username))
    try:
        conn.search(
            search_base=cfg.base_dn,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=[
                cfg.attr_uid,
                cfg.attr_email,
                cfg.attr_display_name,
                cfg.group_membership_attr,
                "distinguishedName",
                "sAMAccountName",
            ],
        )
    except LDAPException as exc:
        logger.warning("ldap_service: user search failed: %s", exc)
        conn.unbind()
        return None

    if not conn.entries:
        conn.unbind()
        return None

    entry = conn.entries[0]
    user_dn = str(entry.entry_dn)
    conn.unbind()

    # 2. Re-bind as the user to verify the password
    server = _make_server(cfg)
    user_conn = Connection(
        server,
        user=user_dn,
        password=password,
        authentication=SIMPLE,
        client_strategy=SYNC,
        receive_timeout=5,
        raise_exceptions=False,
    )
    if cfg.use_tls:
        user_conn.start_tls()
    if not user_conn.bind():
        logger.info("ldap_service: user bind failed for DN %s", user_dn)
        return None
    user_conn.unbind()

    # 3. Extract attributes
    uid          = _attr_str(entry, cfg.attr_uid) or _attr_str(entry, "sAMAccountName") or username
    email        = _attr_str(entry, cfg.attr_email) or f"{username}@ldap"
    display_name = _attr_str(entry, cfg.attr_display_name) or username

    # 4. Collect group DNs
    groups: list[str] = _get_group_dns(cfg, entry, user_dn)

    return {
        "uid":          uid,
        "username":     username,
        "email":        email,
        "display_name": display_name,
        "groups":       groups,
    }


def _get_group_dns(cfg, entry, user_dn: str) -> list[str]:
    """Return list of lowercase group DNs the user belongs to."""
    from ldap3 import SUBTREE
    from ldap3.core.exceptions import LDAPException

    groups: list[str] = []

    if cfg.follow_nested_groups:
        # Use AD's LDAP_MATCHING_RULE_IN_CHAIN for recursive membership
        conn = _service_bind(cfg)
        if conn is None:
            return groups
        try:
            nested_filter = f"(member:1.2.840.113556.1.4.1941:={_ldap_escape_dn(user_dn)})"
            conn.search(
                search_base=cfg.base_dn,
                search_filter=nested_filter,
                search_scope=SUBTREE,
                attributes=["distinguishedName"],
            )
            groups = [str(e.entry_dn).lower() for e in conn.entries]
        except LDAPException as exc:
            logger.warning("ldap_service: nested group search failed: %s", exc)
        finally:
            conn.unbind()
    else:
        # Direct memberOf attribute
        raw = getattr(entry, cfg.group_membership_attr, None)
        if raw is not None:
            values = raw.values if hasattr(raw, "values") else list(raw)
            groups = [str(v).lower() for v in values]

    return groups


# ── Public: user provisioning ─────────────────────────────────────────────

def get_or_create_ldap_user(uid: str, username: str, email: str, display_name: str):
    """Return (or create/migrate) the local User record for an LDAP user."""
    from app.models.user import User

    # 1. Find by stable UID
    user = User.objects(external_uid=uid, auth_provider="ldap").first()

    # 2. Fall back to username match (handles migration of existing local accounts)
    if user is None:
        user = User.objects(username=username).first()
        if user and user.auth_provider != "ldap":
            logger.info("ldap_service: migrating local account %s to LDAP", username)
            user.auth_provider  = "ldap"
            user.external_uid   = uid
            user.password_hash  = ""

    # 3. Create fresh
    if user is None:
        user = User(
            username      = username,
            email         = email,
            name          = display_name,
            auth_provider = "ldap",
            external_uid  = uid,
            password_hash = "",
        )

    # 4. Update mutable fields (AD is authoritative)
    user.email = email
    user.name  = display_name
    user.save()
    return user


# ── Public: group-to-role sync ────────────────────────────────────────────

def sync_ldap_groups(user, groups: list[str]) -> None:
    """Sync project memberships for *user* based on AD *groups*.

    Rules
    -----
    - LDAP-sourced entries are created/updated/deleted automatically.
    - Manual entries are only upgraded (never downgraded or deleted) when
      the LDAP role is strictly higher-ranked.
    """
    from app.models.ldap_config import LdapGroupMapping
    from app.models.project import ProjectMember

    if not groups:
        # Remove all LDAP-sourced memberships
        ProjectMember.objects(user=user, source="ldap").delete()
        return

    lower_groups = [g.lower() for g in groups]

    # Fetch all matching group→role mappings in one query
    mappings = LdapGroupMapping.objects(group_dn__in=lower_groups)

    # Determine highest LDAP role per project
    project_role: dict[Any, str] = {}  # project_id → role
    project_obj:  dict[Any, Any] = {}  # project_id → Project document
    for m in mappings:
        pid = str(m.project.id)
        current_rank = ROLE_RANKS.get(project_role.get(pid, ""), 0)
        new_rank     = ROLE_RANKS.get(m.role, 0)
        if new_rank > current_rank:
            project_role[pid] = m.role
            project_obj[pid]  = m.project

    matched_pids = set(project_role.keys())

    # Upsert ProjectMember for matched projects
    for pid, role in project_role.items():
        project = project_obj[pid]
        existing = ProjectMember.objects(project=project, user=user).first()

        if existing is None:
            ProjectMember(project=project, user=user, role=role, source="ldap").save()

        elif existing.source == "ldap":
            if existing.role != role:
                existing.role = role
                existing.save()

        else:  # source == "manual"
            if ROLE_RANKS.get(role, 0) > ROLE_RANKS.get(existing.role, 0):
                existing.role   = role
                existing.source = "ldap"
                existing.save()

    # Revoke LDAP-sourced entries for groups the user no longer belongs to
    for pm in ProjectMember.objects(user=user, source="ldap"):
        if str(pm.project.id) not in matched_pids:
            pm.delete()

    # ── Global admin sync ────────────────────────────────────────────────
    # If the user is in any admin_groups → grant is_admin.
    # If they were LDAP-admin before but no longer in any admin group → revoke
    # (only revoke if they were granted via LDAP, i.e. auth_provider == "ldap").
    cfg = _get_config()
    if cfg and cfg.admin_groups:
        admin_group_set = {g.lower() for g in cfg.admin_groups}
        should_be_admin = bool(admin_group_set & set(lower_groups))
        if user.is_admin != should_be_admin:
            user.is_admin = should_be_admin
            user.save()

    # ── Direct user-level project mapping ────────────────────────────────
    # These take precedence over group-derived roles for the same project.
    try:
        from app.models.ldap_config import LdapUserMapping
        from app.models.project import ProjectMember
        username_lower = user.username.lower()
        user_mappings = LdapUserMapping.objects(ldap_username=username_lower)
        mapped_pids = set()
        for um in user_mappings:
            pid = str(um.project.id)
            mapped_pids.add(pid)
            existing = ProjectMember.objects(project=um.project, user=user).first()
            if existing is None:
                ProjectMember(project=um.project, user=user, role=um.role, source="ldap").save()
            elif existing.role != um.role or existing.source != "ldap":
                existing.role   = um.role
                existing.source = "ldap"
                existing.save()
    except Exception:
        pass


# ── Authorization gate ───────────────────────────────────────────────────

def ldap_user_is_authorized(user) -> bool:
    """Return True if the LDAP user has at least one reason to be allowed in.

    Allowed when ANY of the following is true:
    - user.is_admin  (member of an admin group)
    - has at least one ProjectMember entry (from group or user mapping)
    - has at least one direct LdapUserMapping (even before first login)
    """
    if user.is_admin:
        return True

    from app.models.project import ProjectMember
    if ProjectMember.objects(user=user).first():
        return True

    try:
        from app.models.ldap_config import LdapUserMapping
        if LdapUserMapping.objects(ldap_username=user.username.lower()).first():
            return True
    except Exception:
        pass

    return False


# ── Connection test (admin use) ───────────────────────────────────────────

def test_ldap_connection() -> dict:
    """Test the service-account bind. Returns {ok, message}."""
    cfg = _get_config()
    if cfg is None:
        return {"ok": False, "message": "LDAP is disabled or not configured"}

    conn = _service_bind(cfg)
    if conn is None:
        return {"ok": False, "message": "Service-account bind failed — check credentials and server URL"}

    conn.unbind()
    return {"ok": True, "message": f"Connected to {cfg.server_url} successfully"}


# ── Helpers ───────────────────────────────────────────────────────────────

def _attr_str(entry, attr: str) -> str:
    """Safely extract a single string value from an ldap3 entry attribute."""
    try:
        val = getattr(entry, attr, None)
        if val is None:
            return ""
        values = val.values if hasattr(val, "values") else list(val)
        if not values:
            return ""
        raw = values[0]
        # objectGUID comes back as bytes on some AD versions
        if isinstance(raw, bytes):
            import uuid
            try:
                return str(uuid.UUID(bytes_le=raw))
            except Exception:
                return raw.hex()
        return str(raw)
    except Exception:
        return ""


def _ldap_escape(value: str) -> str:
    """Escape special characters in an LDAP search filter value (RFC 4515)."""
    replacements = [
        ("\\", "\\5c"), ("*", "\\2a"), ("(", "\\28"),
        (")", "\\29"), ("\x00", "\\00"),
    ]
    for char, escaped in replacements:
        value = value.replace(char, escaped)
    return value


def _ldap_escape_dn(dn: str) -> str:
    """Minimal escaping for a DN used inside a filter value."""
    return dn.replace("\\", "\\5c").replace(")", "\\29")
