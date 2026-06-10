"""Tests for /api/custom-apps endpoints."""
from __future__ import annotations


class TestCustomApps:
    def test_create_custom_app(self, client, auth_headers):
        rv = client.post("/api/custom-apps/", json={
            "slug": "mytool",
            "title": "My Tool",
            "executable": "/usr/bin/mytool",
        }, headers=auth_headers)
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["slug"] == "mytool"
        assert data["executable"] == "/usr/bin/mytool"

    def test_create_builtin_slug_fails(self, client, auth_headers):
        rv = client.post("/api/custom-apps/", json={
            "slug": "ansible",
            "title": "Ansible Clone",
            "executable": "/usr/bin/ansible-playbook",
        }, headers=auth_headers)
        assert rv.status_code == 400

    def test_duplicate_slug_fails(self, client, auth_headers):
        client.post("/api/custom-apps/", json={
            "slug": "mytool", "title": "T", "executable": "/bin/t",
        }, headers=auth_headers)
        rv = client.post("/api/custom-apps/", json={
            "slug": "mytool", "title": "T2", "executable": "/bin/t2",
        }, headers=auth_headers)
        assert rv.status_code == 409

    def test_list_custom_apps(self, client, auth_headers):
        client.post("/api/custom-apps/", json={
            "slug": "tool1", "title": "T1", "executable": "/bin/t1",
        }, headers=auth_headers)
        rv = client.get("/api/custom-apps/", headers=auth_headers)
        assert rv.status_code == 200
        assert len(rv.get_json()) == 1

    def test_non_admin_cannot_create(self, client, user_headers):
        rv = client.post("/api/custom-apps/", json={
            "slug": "foo", "title": "Foo", "executable": "/bin/foo",
        }, headers=user_headers)
        assert rv.status_code == 403

    def test_custom_app_usable_in_template(self, client, auth_headers, project):
        client.post("/api/custom-apps/", json={
            "slug": "mytool", "title": "My Tool", "executable": "/usr/bin/mytool",
        }, headers=auth_headers)

        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "Custom Template", "app": "mytool", "playbook": "run.sh"},
            headers=auth_headers,
        )
        assert rv.status_code == 201
        assert rv.get_json()["app"] == "mytool"

    def test_update_custom_app(self, client, auth_headers):
        rv = client.post("/api/custom-apps/", json={
            "slug": "mytool", "title": "Old", "executable": "/bin/old",
        }, headers=auth_headers)
        app_id = rv.get_json()["id"]

        rv2 = client.put(f"/api/custom-apps/{app_id}", json={
            "slug": "mytool", "title": "New", "executable": "/bin/new",
        }, headers=auth_headers)
        assert rv2.status_code == 200
        assert rv2.get_json()["title"] == "New"

    def test_delete_custom_app(self, client, auth_headers):
        rv = client.post("/api/custom-apps/", json={
            "slug": "mytool", "title": "T", "executable": "/bin/t",
        }, headers=auth_headers)
        app_id = rv.get_json()["id"]

        rv2 = client.delete(f"/api/custom-apps/{app_id}", headers=auth_headers)
        assert rv2.status_code == 200
