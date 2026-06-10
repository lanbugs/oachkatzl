"""Tests for auth_service (passwords, JWT, TOTP, recovery codes)."""
import pytest
import jwt as pyjwt

from app.services.auth_service import (
    hash_password, verify_password,
    create_access_token, create_2fa_pending_token, decode_token,
    TOKEN_TYPE_ACCESS, TOKEN_TYPE_2FA_PENDING,
    generate_api_token, verify_api_token,
    generate_totp_secret, verify_totp, get_totp_uri,
    generate_recovery_codes, hash_recovery_code,
)
from app.services.crypto import encrypt


class TestPasswords:
    def test_hash_and_verify(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h)

    def test_wrong_password_fails(self):
        h = hash_password("correct")
        assert not verify_password("wrong", h)

    def test_empty_password(self):
        h = hash_password("")
        assert verify_password("", h)
        assert not verify_password("notempty", h)


class TestJWT:
    def test_access_token_roundtrip(self):
        token = create_access_token("user123")
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["type"] == TOKEN_TYPE_ACCESS

    def test_2fa_pending_token(self):
        token = create_2fa_pending_token("user456")
        payload = decode_token(token)
        assert payload["sub"] == "user456"
        assert payload["type"] == TOKEN_TYPE_2FA_PENDING

    def test_expired_token_raises(self):
        import datetime
        import jwt
        payload = {
            "sub": "u1",
            "type": TOKEN_TYPE_ACCESS,
            "exp": datetime.datetime.utcnow() - datetime.timedelta(seconds=1),
        }
        from app.config import settings
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_token(token)

    def test_tampered_token_raises(self):
        token = create_access_token("u1") + "tampered"
        with pytest.raises(pyjwt.PyJWTError):
            decode_token(token)


class TestApiTokens:
    def test_generate_and_verify(self):
        raw, hash_ = generate_api_token()
        assert verify_api_token(raw, hash_)
        assert not verify_api_token("wrong", hash_)

    def test_tokens_are_unique(self):
        raw1, _ = generate_api_token()
        raw2, _ = generate_api_token()
        assert raw1 != raw2


class TestTOTP:
    def test_secret_generation(self):
        secret = generate_totp_secret()
        assert len(secret) >= 16

    def test_verify_valid_code(self):
        import pyotp
        secret = generate_totp_secret()
        encrypted_secret = encrypt(secret)
        code = pyotp.TOTP(secret).now()
        assert verify_totp(encrypted_secret, code)

    def test_verify_invalid_code(self):
        secret = generate_totp_secret()
        encrypted_secret = encrypt(secret)
        assert not verify_totp(encrypted_secret, "000000")

    def test_verify_empty_secret(self):
        assert not verify_totp("", "123456")

    def test_totp_uri_format(self):
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "alice")
        assert "otpauth://totp/" in uri
        assert "alice" in uri


class TestRecoveryCodes:
    def test_generate_8_codes(self):
        codes = generate_recovery_codes(8)
        assert len(codes) == 8
        assert all("-" in c for c in codes)

    def test_codes_are_unique(self):
        codes = generate_recovery_codes(8)
        assert len(set(codes)) == 8

    def test_hash_and_verify(self, app):
        """End-to-end: generate → hash → store on User → verify+consume."""
        from app.models.user import User
        from app.services.auth_service import (
            verify_and_consume_recovery_code, hash_recovery_code,
        )
        codes = generate_recovery_codes(4)
        user = User(
            username="rtest", email="rtest@test.com",
            password_hash=hash_password("x"), active=True,
            recovery_codes=[hash_recovery_code(c) for c in codes],
        ).save()

        assert verify_and_consume_recovery_code(user, codes[0])
        user.reload()
        assert len(user.recovery_codes) == 3  # consumed

    def test_wrong_code_fails(self, app):
        from app.models.user import User
        from app.services.auth_service import verify_and_consume_recovery_code
        codes = generate_recovery_codes(2)
        user = User(
            username="rtest2", email="rtest2@test.com",
            password_hash=hash_password("x"), active=True,
            recovery_codes=[hash_recovery_code(c) for c in codes],
        ).save()
        assert not verify_and_consume_recovery_code(user, "XXXX-XXXX")
