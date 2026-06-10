from __future__ import annotations

import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    ListField,
    ReferenceField,
    StringField,
    DENY,
)


class User(Document):
    meta = {"collection": "users", "indexes": ["username", "email"]}

    username = StringField(required=True, unique=True, max_length=150)
    # StringField instead of EmailField — EmailField rejects localhost domains
    email = StringField(required=True, unique=True, max_length=255)
    name = StringField(max_length=255, default="")
    password_hash = StringField(default="")
    is_admin = BooleanField(default=False)
    active = BooleanField(default=True)
    auth_provider = StringField(
        choices=("local", "ldap", "oidc"), default="local"
    )
    external_uid = StringField(default="")
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    last_login = DateTimeField()
    # 2FA
    totp_secret = StringField(default="")   # stored Fernet-encrypted
    totp_enabled = BooleanField(default=False)
    recovery_codes = ListField(StringField())  # argon2-hashed codes


class ApiToken(Document):
    meta = {"collection": "api_tokens", "indexes": ["user"]}

    user = ReferenceField(User, required=True, reverse_delete_rule=DENY)
    token_hash = StringField(required=True, unique=True)
    name = StringField(required=True, max_length=255)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    expires_at = DateTimeField()
    revoked = BooleanField(default=False)
