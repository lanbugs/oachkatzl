from __future__ import annotations

import datetime

from apiflask import APIBlueprint, HTTPError
from flask import g

from app.extensions import limiter
from app.schemas.auth import (
    LoginIn, LoginOut, Verify2FAIn, TokenOut,
    ApiTokenCreateIn, ApiTokenOut, ApiTokenCreatedOut,
    TOTP2FASetupOut, TOTP2FAEnableIn, TOTP2FAEnableOut,
    RecoveryCodeIn, UserOut, ChangePasswordIn, Disable2FAIn,
)
from app.services.rbac import require_auth

bp = APIBlueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
@limiter.limit("20/minute")
@bp.input(LoginIn, arg_name="body")
@bp.output(LoginOut)
def login(body):
    from app.models.user import User
    from app.services.auth_service import (
        verify_password, create_access_token, create_2fa_pending_token,
        create_2fa_setup_pending_token, _get_dummy_hash,
    )
    from app.services.ldap_service import (
        ldap_authenticate, get_or_create_ldap_user, sync_ldap_groups,
        ldap_user_is_authorized,
    )

    username = body["username"]
    password = body["password"]

    user = User.objects(username=username, active=True).first()

    if user and user.auth_provider == "ldap":
        # ── LDAP user: always authenticate via LDAP ───────────────────────
        ldap_info = ldap_authenticate(username, password)
        if not ldap_info:
            raise HTTPError(401, "Invalid credentials")
        user = get_or_create_ldap_user(
            uid          = ldap_info["uid"],
            username     = ldap_info["username"],
            email        = ldap_info["email"],
            display_name = ldap_info["display_name"],
        )
        sync_ldap_groups(user, ldap_info["groups"])
        if not ldap_user_is_authorized(user):
            raise HTTPError(401, "No project access configured for this account — contact your administrator")

    elif user and user.auth_provider == "local":
        # ── Local user: standard password check ──────────────────────────
        if not verify_password(password, user.password_hash):
            raise HTTPError(401, "Invalid credentials")

    else:
        # ── Unknown user: run constant-time dummy check, then try LDAP ───
        verify_password(password, _get_dummy_hash())
        ldap_info = ldap_authenticate(username, password)
        if ldap_info:
            user = get_or_create_ldap_user(
                uid          = ldap_info["uid"],
                username     = ldap_info["username"],
                email        = ldap_info["email"],
                display_name = ldap_info["display_name"],
            )
            if not user.active:
                raise HTTPError(401, "Account is disabled")
            sync_ldap_groups(user, ldap_info["groups"])
            if not ldap_user_is_authorized(user):
                raise HTTPError(401, "No project access configured for this account — contact your administrator")
        else:
            raise HTTPError(401, "Invalid credentials")

    if not user.active:
        raise HTTPError(401, "Account is disabled")

    user.last_login = datetime.datetime.utcnow()
    user.save()

    if user.totp_enabled:
        return {
            "requires_2fa": True,
            "temp_token": create_2fa_pending_token(str(user.id)),
            "token": "",
            "user_id": str(user.id),
        }

    # Check global MFA-enforce setting
    from app.models.option import Option
    mfa_required = Option.objects(key="mfa_required").first()
    if mfa_required and mfa_required.value in ("true", "True", "1", True):
        return {
            "requires_2fa": False,
            "mfa_setup_required": True,
            "token": create_2fa_setup_pending_token(str(user.id)),
        }

    return {"token": create_access_token(str(user.id)), "requires_2fa": False}


@bp.post("/login/verify-2fa")
@limiter.limit("10/minute")
@bp.input(Verify2FAIn, arg_name="body")
@bp.output(TokenOut)
def verify_2fa(body):
    import jwt as pyjwt
    from app.models.user import User
    from app.services.auth_service import (
        verify_totp, verify_and_consume_recovery_code,
        create_access_token, decode_token, TOKEN_TYPE_2FA_PENDING,
    )

    try:
        payload = decode_token(body["temp_token"])
    except pyjwt.PyJWTError:
        raise HTTPError(401, "Invalid or expired 2FA token")

    if payload.get("type") != TOKEN_TYPE_2FA_PENDING:
        raise HTTPError(401, "Invalid token type")

    try:
        user = User.objects.get(id=payload["sub"], active=True)
    except User.DoesNotExist:
        raise HTTPError(401, "Invalid or expired 2FA token")

    code = body["code"].strip()
    if not (
        verify_totp(user.totp_secret, code)
        or verify_and_consume_recovery_code(user, code)
    ):
        raise HTTPError(401, "Invalid 2FA code")

    return {"token": create_access_token(str(user.id))}


@bp.get("/me")
@require_auth
@bp.output(UserOut)
def me():
    from app.models.option import Option
    u = g.current_user
    mfa_opt = Option.objects(key="mfa_required").first()
    mfa_enforce = bool(mfa_opt and mfa_opt.value in ("true", "True", "1"))
    return {
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "name": u.name,
        "is_admin": u.is_admin,
        "active": u.active,
        "auth_provider": u.auth_provider,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "totp_enabled": u.totp_enabled,
        "mfa_setup_required": mfa_enforce and not u.totp_enabled,
    }


# ── Change password ───────────────────────────────────────────────────────

@bp.post("/change-password")
@require_auth
@bp.input(ChangePasswordIn, arg_name="body")
def change_password(body):
    from app.services.auth_service import verify_password, hash_password

    user = g.current_user

    # LDAP / external users cannot set a local password
    if user.auth_provider != "local":
        raise HTTPError(400, "Password change is not available for external accounts (LDAP/OIDC).")

    if not verify_password(body["current_password"], user.password_hash):
        raise HTTPError(400, "Current password is incorrect.")

    user.password_hash = hash_password(body["new_password"])
    user.save()
    return {"message": "Password changed successfully."}, 200


# ── API Tokens ────────────────────────────────────────────────────────────

@bp.get("/tokens")
@require_auth
@bp.output(ApiTokenOut(many=True))
def list_tokens():
    from app.models.user import ApiToken
    tokens = ApiToken.objects(user=g.current_user, revoked=False)
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "created_at": t.created_at.isoformat(),
            "expires_at": t.expires_at.isoformat() if t.expires_at else None,
            "revoked": t.revoked,
        }
        for t in tokens
    ]


@bp.post("/tokens")
@require_auth
@bp.input(ApiTokenCreateIn, arg_name="body")
@bp.output(ApiTokenCreatedOut, status_code=201)
def create_token(body):
    from app.models.user import ApiToken
    from app.services.auth_service import generate_api_token, create_api_token_jwt

    raw, hash_ = generate_api_token()
    expires_at = None
    if body.get("expires_at"):
        try:
            expires_at = datetime.datetime.fromisoformat(body["expires_at"])
        except ValueError:
            raise HTTPError(400, "Invalid expires_at format")

    api_token = ApiToken(
        user=g.current_user,
        token_hash=hash_,
        name=body["name"],
        expires_at=expires_at,
    ).save()

    jwt_token = create_api_token_jwt(str(api_token.id), raw)
    return {"id": str(api_token.id), "name": api_token.name, "token": jwt_token}


@bp.delete("/tokens/<token_id>")
@require_auth
def revoke_token(token_id):
    from app.models.user import ApiToken
    try:
        t = ApiToken.objects.get(id=token_id, user=g.current_user)
    except ApiToken.DoesNotExist:
        raise HTTPError(404, "Token not found")
    t.revoked = True
    t.save()
    return {"message": "Token revoked"}, 200


# ── 2FA Management ────────────────────────────────────────────────────────

@bp.get("/2fa/setup")
@require_auth
@bp.output(TOTP2FASetupOut)
def totp_setup():
    from app.services.auth_service import generate_totp_secret, generate_qr_svg
    from app.services.crypto import encrypt

    secret = generate_totp_secret()
    qr_svg = generate_qr_svg(secret, g.current_user.username)

    # Store encrypted secret temporarily (not yet enabled)
    g.current_user.totp_secret = encrypt(secret)
    g.current_user.totp_enabled = False
    g.current_user.save()

    return {"secret": secret, "qr_svg": qr_svg}


@bp.post("/2fa/enable")
@require_auth
@bp.input(TOTP2FAEnableIn, arg_name="body")
@bp.output(TOTP2FAEnableOut, status_code=201)
def totp_enable(body):
    from app.services.auth_service import (
        verify_totp, generate_recovery_codes, hash_recovery_code,
    )

    user = g.current_user
    if not user.totp_secret:
        raise HTTPError(400, "Call /2fa/setup first")

    if not verify_totp(user.totp_secret, body["code"]):
        raise HTTPError(400, "Invalid TOTP code")

    codes = generate_recovery_codes()
    user.recovery_codes = [hash_recovery_code(c) for c in codes]
    user.totp_enabled = True
    user.save()

    return {"recovery_codes": codes}


@bp.post("/2fa/disable")
@require_auth
@bp.input(Disable2FAIn, arg_name="body")
def totp_disable(body):
    from app.services.auth_service import verify_totp

    user = g.current_user
    if not user.totp_enabled:
        raise HTTPError(400, "2FA is not enabled")
    if not verify_totp(user.totp_secret, body["code"]):
        raise HTTPError(400, "Invalid 2FA code")

    user.totp_enabled = False
    user.totp_secret = ""
    user.recovery_codes = []
    user.save()
    return {"message": "2FA disabled"}, 200
