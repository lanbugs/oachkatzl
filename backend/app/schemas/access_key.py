from apiflask.fields import Boolean, String
from apiflask.schemas import Schema
from marshmallow import validate

KEY_TYPES = ("none", "ssh", "login_password", "vault")


class AccessKeyIn(Schema):
    name = String(required=True, validate=validate.Length(min=1, max=255))
    type = String(required=True, validate=validate.OneOf(KEY_TYPES))
    # Type-specific secret fields (all optional, validated in service)
    private_key = String(load_default=None)
    passphrase = String(load_default=None)
    login = String(load_default=None)
    password = String(load_default=None)
    vault_password = String(load_default=None)


class AccessKeyOut(Schema):
    id = String()
    name = String()
    type = String()
    created_at = String()
    has_secret = Boolean()   # never expose the secret itself
