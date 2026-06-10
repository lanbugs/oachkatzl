from apiflask.fields import Boolean, List, String
from apiflask.schemas import Schema
from marshmallow import validate


class LoginIn(Schema):
    username = String(required=True)
    password = String(required=True)


class LoginOut(Schema):
    token = String()
    requires_2fa = Boolean(dump_default=False)
    mfa_setup_required = Boolean(dump_default=False)
    temp_token = String(dump_default=None)
    user_id = String()


class Verify2FAIn(Schema):
    temp_token = String(required=True)
    code = String(required=True)


class TokenOut(Schema):
    token = String()


class ApiTokenCreateIn(Schema):
    name = String(required=True, validate=validate.Length(min=1, max=255))
    expires_at = String(load_default=None)


class ApiTokenOut(Schema):
    id = String()
    name = String()
    created_at = String()
    expires_at = String(dump_default=None)
    revoked = Boolean()


class ApiTokenCreatedOut(Schema):
    id = String()
    name = String()
    token = String()   # raw token, shown only once


class TOTP2FASetupOut(Schema):
    secret = String()
    qr_svg = String()


class TOTP2FAEnableIn(Schema):
    code = String(required=True)


class TOTP2FAEnableOut(Schema):
    recovery_codes = List(String())


class RecoveryCodeIn(Schema):
    code = String(required=True)


class Disable2FAIn(Schema):
    code = String(required=True)


class ChangePasswordIn(Schema):
    current_password = String(required=True)
    new_password = String(required=True, validate=validate.Length(min=8))


class UserOut(Schema):
    id = String()
    username = String()
    email = String()
    name = String()
    is_admin = Boolean()
    active = Boolean()
    auth_provider = String()
    created_at = String()
    last_login = String(dump_default=None)
    totp_enabled = Boolean()
    mfa_setup_required = Boolean(dump_default=False)
