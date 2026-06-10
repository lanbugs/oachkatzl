"""Tests for /api/auth endpoints."""
from __future__ import annotations

import pytest


class TestLogin:
    def test_login_success(self, client, admin_user):
        rv = client.post("/api/auth/login", json={"username": "admin", "password": "adminpass"})
        assert rv.status_code == 200
        data = rv.get_json()
        assert "token" in data
        assert data["requires_2fa"] is False

    def test_login_wrong_password(self, client, admin_user):
        rv = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert rv.status_code == 401

    def test_login_unknown_user(self, client):
        rv = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
        assert rv.status_code == 401

    def test_login_inactive_user(self, client, app):
        from app.models.user import User
        from app.services.auth_service import hash_password
        User(
            username="inactive", email="inactive@test.com",
            password_hash=hash_password("pass"), active=False,
        ).save()
        rv = client.post("/api/auth/login", json={"username": "inactive", "password": "pass"})
        assert rv.status_code == 401

    def test_health_endpoint(self, client):
        rv = client.get("/api/health")
        assert rv.status_code == 200


class TestMe:
    def test_me_authenticated(self, client, auth_headers):
        rv = client.get("/api/auth/me", headers=auth_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["username"] == "admin"
        assert data["is_admin"] is True

    def test_me_unauthenticated(self, client):
        rv = client.get("/api/auth/me")
        assert rv.status_code == 401

    def test_me_invalid_token(self, client):
        rv = client.get("/api/auth/me", headers={"Authorization": "Bearer bad.token.here"})
        assert rv.status_code == 401


class TestApiTokens:
    def test_create_and_list_token(self, client, auth_headers):
        rv = client.post("/api/auth/tokens", json={"name": "ci-token"}, headers=auth_headers)
        assert rv.status_code == 201
        data = rv.get_json()
        assert "token" in data
        assert data["name"] == "ci-token"

        rv2 = client.get("/api/auth/tokens", headers=auth_headers)
        assert rv2.status_code == 200
        assert len(rv2.get_json()) == 1

    def test_revoke_token(self, client, auth_headers):
        rv = client.post("/api/auth/tokens", json={"name": "temp"}, headers=auth_headers)
        token_id = rv.get_json()["id"]

        rv2 = client.delete(f"/api/auth/tokens/{token_id}", headers=auth_headers)
        assert rv2.status_code == 200

        rv3 = client.get("/api/auth/tokens", headers=auth_headers)
        assert len(rv3.get_json()) == 0


class TestTwoFactor:
    def test_setup_returns_secret_and_qr(self, client, auth_headers):
        rv = client.get("/api/auth/2fa/setup", headers=auth_headers)
        assert rv.status_code == 200
        data = rv.get_json()
        assert "secret" in data
        assert "qr_svg" in data
        assert "<svg" in data["qr_svg"]

    def test_enable_2fa_with_valid_code(self, client, auth_headers, admin_user):
        import pyotp
        from app.services.auth_service import generate_totp_secret
        from app.services.crypto import encrypt

        secret = generate_totp_secret()
        admin_user.totp_secret = encrypt(secret)
        admin_user.totp_enabled = False
        admin_user.save()

        code = pyotp.TOTP(secret).now()
        rv = client.post("/api/auth/2fa/enable", json={"code": code}, headers=auth_headers)
        assert rv.status_code == 201
        data = rv.get_json()
        assert "recovery_codes" in data
        assert len(data["recovery_codes"]) > 0

        admin_user.reload()
        assert admin_user.totp_enabled is True

    def test_enable_2fa_with_invalid_code(self, client, auth_headers, admin_user):
        from app.services.auth_service import generate_totp_secret
        from app.services.crypto import encrypt

        admin_user.totp_secret = encrypt(generate_totp_secret())
        admin_user.save()

        rv = client.post("/api/auth/2fa/enable", json={"code": "000000"}, headers=auth_headers)
        assert rv.status_code == 400

    def test_login_with_2fa_requires_verification(self, client, admin_user):
        import pyotp
        from app.services.auth_service import generate_totp_secret
        from app.services.crypto import encrypt

        secret = generate_totp_secret()
        admin_user.totp_secret = encrypt(secret)
        admin_user.totp_enabled = True
        admin_user.save()

        rv = client.post("/api/auth/login", json={"username": "admin", "password": "adminpass"})
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["requires_2fa"] is True
        assert "temp_token" in data

        code = pyotp.TOTP(secret).now()
        rv2 = client.post("/api/auth/login/verify-2fa", json={
            "temp_token": data["temp_token"],
            "code": code,
        })
        assert rv2.status_code == 200
        assert "token" in rv2.get_json()

    def test_login_2fa_wrong_code(self, client, admin_user):
        from app.services.auth_service import generate_totp_secret
        from app.services.crypto import encrypt

        secret = generate_totp_secret()
        admin_user.totp_secret = encrypt(secret)
        admin_user.totp_enabled = True
        admin_user.save()

        rv = client.post("/api/auth/login", json={"username": "admin", "password": "adminpass"})
        temp_token = rv.get_json()["temp_token"]

        rv2 = client.post("/api/auth/login/verify-2fa", json={
            "temp_token": temp_token, "code": "000000",
        })
        assert rv2.status_code == 401

    def test_disable_2fa(self, client, auth_headers, admin_user):
        import pyotp
        from app.services.crypto import encrypt

        secret = pyotp.random_base32()
        admin_user.totp_enabled = True
        admin_user.totp_secret = encrypt(secret)
        admin_user.save()

        code = pyotp.TOTP(secret).now()
        rv = client.post("/api/auth/2fa/disable", json={"code": code}, headers=auth_headers)
        assert rv.status_code == 200
        admin_user.reload()
        assert admin_user.totp_enabled is False
