from __future__ import annotations

import datetime
import io
import secrets
import string

import jwt
import pyotp
import qrcode
import qrcode.image.svg
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from app.config import settings
from app.services.crypto import encrypt, decrypt

_ph = PasswordHasher()

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_2FA_PENDING = "2fa_pending"
TOKEN_TYPE_2FA_SETUP_PENDING = "2fa_setup_pending"
TOKEN_TYPE_API = "api"

# Dummy hash used for constant-time password checks when the user does not exist.
# Prevents username enumeration via timing differences.
_DUMMY_HASH = None


def _get_dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = _ph.hash("dummy-placeholder-000000000000000")
    return _DUMMY_HASH


# ── Passwords ──────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hash_: str) -> bool:
    try:
        return _ph.verify(hash_, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# ── JWT ────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": TOKEN_TYPE_ACCESS,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_2fa_pending_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": TOKEN_TYPE_2FA_PENDING,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow()
        + datetime.timedelta(minutes=settings.JWT_2FA_PENDING_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def create_2fa_setup_pending_token(user_id: str) -> str:
    """Issue a restricted token for users who must enroll 2FA before accessing the app."""
    payload = {
        "sub": user_id,
        "type": TOKEN_TYPE_2FA_SETUP_PENDING,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and return payload; raises jwt.PyJWTError on invalid/expired."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])


# ── API tokens ─────────────────────────────────────────────────────────────

def generate_api_token() -> tuple[str, str]:
    """Return (raw_token, hash) pair. Only raw is shown to the user once."""
    raw = secrets.token_urlsafe(40)
    return raw, _ph.hash(raw)


def create_api_token_jwt(api_token_id: str, raw: str) -> str:
    """Wrap a raw API token in a signed JWT for use as a Bearer token."""
    payload = {
        "sub": api_token_id,
        "type": TOKEN_TYPE_API,
        "raw": raw,
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_api_token(raw: str, hash_: str) -> bool:
    return verify_password(raw, hash_)


# ── TOTP / 2FA ─────────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username, issuer_name=settings.TOTP_ISSUER
    )


def generate_qr_svg(secret: str, username: str) -> str:
    uri = get_totp_uri(secret, username)
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(uri, image_factory=factory)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode()


def verify_totp(encrypted_secret: str, code: str) -> bool:
    secret = decrypt(encrypted_secret)
    if not secret:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)


# ── Recovery codes ─────────────────────────────────────────────────────────

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_recovery_codes(n: int = 8) -> list[str]:
    """Return n human-readable recovery codes."""
    return [
        "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
        + "-"
        + "".join(secrets.choice(_CODE_ALPHABET) for _ in range(4))
        for _ in range(n)
    ]


def hash_recovery_code(code: str) -> str:
    return _ph.hash(code.upper().replace("-", ""))


def verify_and_consume_recovery_code(user, code: str) -> bool:
    """Verify code against stored hashes; removes matching hash on success."""
    normalized = code.upper().replace("-", "")
    for idx, hashed in enumerate(user.recovery_codes or []):
        try:
            if _ph.verify(hashed, normalized):
                user.recovery_codes.pop(idx)
                user.save()
                return True
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            continue
    return False
