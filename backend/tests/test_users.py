"""Tests for /api/users endpoints."""


class TestUsers:
    def test_list_users_admin(self, client, auth_headers, admin_user):
        rv = client.get("/api/users/", headers=auth_headers)
        assert rv.status_code == 200
        assert len(rv.get_json()) >= 1

    def test_list_users_non_admin_forbidden(self, client, user_headers):
        rv = client.get("/api/users/", headers=user_headers)
        assert rv.status_code == 403

    def test_create_user(self, client, auth_headers):
        rv = client.post("/api/users/", json={
            "username": "bob", "email": "bob@test.com",
            "password": "bobpassword", "name": "Bob",
        }, headers=auth_headers)
        assert rv.status_code == 201
        assert rv.get_json()["username"] == "bob"

    def test_create_duplicate_username(self, client, auth_headers, admin_user):
        rv = client.post("/api/users/", json={
            "username": "admin", "email": "other@test.com", "password": "xxxxxxxx",
        }, headers=auth_headers)
        assert rv.status_code == 409

    def test_get_user_self(self, client, user_headers, regular_user):
        rv = client.get(f"/api/users/{regular_user.id}", headers=user_headers)
        assert rv.status_code == 200
        assert rv.get_json()["username"] == "alice"

    def test_get_user_other_forbidden(self, client, user_headers, admin_user):
        rv = client.get(f"/api/users/{admin_user.id}", headers=user_headers)
        assert rv.status_code == 403

    def test_update_user(self, client, auth_headers, regular_user):
        rv = client.put(f"/api/users/{regular_user.id}", json={
            "email": "new@test.com", "name": "New Name",
        }, headers=auth_headers)
        assert rv.status_code == 200
        assert rv.get_json()["email"] == "new@test.com"

    def test_delete_user(self, client, auth_headers):
        rv = client.post("/api/users/", json={
            "username": "todelete", "email": "del@test.com", "password": "xxxxxxxx",
        }, headers=auth_headers)
        uid = rv.get_json()["id"]
        rv2 = client.delete(f"/api/users/{uid}", headers=auth_headers)
        assert rv2.status_code == 200
