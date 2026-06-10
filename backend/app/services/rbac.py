from __future__ import annotations

import functools

import jwt
from apiflask import HTTPError
from flask import g, request

from app.services.auth_service import (
    decode_token, TOKEN_TYPE_ACCESS, TOKEN_TYPE_API, TOKEN_TYPE_2FA_SETUP_PENDING,
)

ROLE_RANKS = {"owner": 4, "manager": 3, "task_runner": 2, "guest": 1}


def _extract_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def _load_user_from_token(token: str):
    from app.models.user import User, ApiToken

    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None, None

    token_type = payload.get("type")
    user_id = payload.get("sub")

    if token_type in (TOKEN_TYPE_ACCESS, TOKEN_TYPE_2FA_SETUP_PENDING):
        try:
            user = User.objects.get(id=user_id, active=True)
            return user, token_type
        except User.DoesNotExist:
            return None, None

    if token_type == TOKEN_TYPE_API:
        # API tokens: sub is the ApiToken id, verify raw vs hash
        raw = payload.get("raw", "")
        try:
            api_token = ApiToken.objects.get(id=user_id, revoked=False)
            # Reject expired tokens
            if api_token.expires_at:
                import datetime
                if api_token.expires_at < datetime.datetime.utcnow():
                    return None, None
            from app.services.auth_service import verify_api_token
            if verify_api_token(raw, api_token.token_hash):
                return api_token.user, token_type
        except ApiToken.DoesNotExist:
            pass
        return None, None

    return None, None


# Public alias for reuse outside the decorators (e.g. SocketIO handshake auth).
def load_user_from_token(token: str):
    """Return (user, token_type) for a bearer token, or (None, None)."""
    return _load_user_from_token(token)


def user_can_access_project(user, project_id: str) -> bool:
    """True if *user* is an admin or a member of the given project."""
    if user is None:
        return False
    if getattr(user, "is_admin", False):
        return True
    from app.models.project import Project, ProjectMember

    try:
        project = Project.objects.get(id=project_id)
    except (Project.DoesNotExist, Exception):
        return False
    return ProjectMember.objects(project=project, user=user).first() is not None


def require_auth(f):
    """Decorator: sets g.current_user or raises 401.

    2fa_setup_pending tokens are restricted to /api/auth/* endpoints only.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            raise HTTPError(401, "Authentication required")
        user, token_type = _load_user_from_token(token)
        if user is None:
            raise HTTPError(401, "Invalid or expired token")

        if token_type == TOKEN_TYPE_2FA_SETUP_PENDING:
            if not request.path.startswith("/api/auth/"):
                raise HTTPError(
                    403,
                    "2FA enrollment required — complete 2FA setup before accessing this resource",
                )

        g.current_user = user
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    @functools.wraps(f)
    @require_auth
    def wrapper(*args, **kwargs):
        if not g.current_user.is_admin:
            raise HTTPError(403, "Admin access required")
        return f(*args, **kwargs)
    return wrapper


def require_project_role(*roles: str):
    """Decorator factory: requires current user to be a project member with one of the given roles.

    The decorated view must have a `project_id` URL parameter.
    Sets g.project and g.membership.
    Admins bypass role checks (they can access everything).
    """
    def decorator(f):
        @functools.wraps(f)
        @require_auth
        def wrapper(*args, **kwargs):
            from app.models.project import Project, ProjectMember

            project_id = kwargs.get("project_id")
            try:
                project = Project.objects.get(id=project_id)
            except (Project.DoesNotExist, Exception):
                raise HTTPError(404, "Project not found")

            g.project = project

            if g.current_user.is_admin:
                g.membership = None
                return f(*args, **kwargs)

            try:
                membership = ProjectMember.objects.get(
                    project=project, user=g.current_user
                )
            except ProjectMember.DoesNotExist:
                raise HTTPError(403, "Not a project member")

            if roles and membership.role not in roles:
                raise HTTPError(403, f"Requires one of roles: {', '.join(roles)}")

            g.membership = membership
            return f(*args, **kwargs)
        return wrapper
    return decorator


def get_current_project_role() -> str | None:
    """Return the current user's role in g.project, or 'owner' for admins."""
    if g.current_user.is_admin:
        return "owner"
    m = getattr(g, "membership", None)
    return m.role if m else None
