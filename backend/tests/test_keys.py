"""Tests for Access Key endpoints + encryption."""
from __future__ import annotations

import json


class TestAccessKeys:
    def test_create_ssh_key(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/keys/",
            json={
                "name": "Deploy Key",
                "type": "ssh",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
                "passphrase": "",
            },
            headers=auth_headers,
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["type"] == "ssh"
        assert data["has_secret"] is True
        assert "private_key" not in data  # never exposed

    def test_create_login_password_key(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/keys/",
            json={"name": "DB Creds", "type": "login_password", "login": "root", "password": "s3cr3t"},
            headers=auth_headers,
        )
        assert rv.status_code == 201
        assert rv.get_json()["type"] == "login_password"

    def test_create_vault_key(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/keys/",
            json={"name": "Vault PW", "type": "vault", "vault_password": "vaultpass"},
            headers=auth_headers,
        )
        assert rv.status_code == 201

    def test_secret_is_encrypted_in_db(self, client, auth_headers, project):
        from app.models.access_key import AccessKey
        from app.services.crypto import decrypt
        import json

        client.post(
            f"/api/projects/{project.id}/keys/",
            json={"name": "Encrypted", "type": "vault", "vault_password": "mysecret"},
            headers=auth_headers,
        )
        key = AccessKey.objects.first()
        assert key.secret != "mysecret"  # not plaintext
        decrypted = json.loads(decrypt(key.secret))
        assert decrypted["vault_password"] == "mysecret"

    def test_list_keys(self, client, auth_headers, project):
        client.post(
            f"/api/projects/{project.id}/keys/",
            json={"name": "K1", "type": "none"},
            headers=auth_headers,
        )
        rv = client.get(f"/api/projects/{project.id}/keys/", headers=auth_headers)
        assert rv.status_code == 200
        assert len(rv.get_json()) == 1

    def test_delete_key(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/keys/",
            json={"name": "TempKey", "type": "none"},
            headers=auth_headers,
        )
        key_id = rv.get_json()["id"]
        rv2 = client.delete(f"/api/projects/{project.id}/keys/{key_id}", headers=auth_headers)
        assert rv2.status_code == 200
