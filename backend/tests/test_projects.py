"""Tests for /api/projects endpoints and RBAC."""
from __future__ import annotations

import pytest


class TestProjectCRUD:
    def test_create_project(self, client, auth_headers):
        rv = client.post("/api/projects/", json={"name": "My Project"}, headers=auth_headers)
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["name"] == "My Project"
        assert "id" in data

    def test_list_projects_admin_sees_all(self, client, auth_headers, project):
        rv = client.get("/api/projects/", headers=auth_headers)
        assert rv.status_code == 200
        assert len(rv.get_json()) >= 1

    def test_list_projects_user_sees_own(self, client, user_headers, regular_user):
        rv = client.get("/api/projects/", headers=user_headers)
        assert rv.status_code == 200
        assert rv.get_json() == []

    def test_get_project(self, client, auth_headers, project):
        rv = client.get(f"/api/projects/{project.id}", headers=auth_headers)
        assert rv.status_code == 200
        assert rv.get_json()["id"] == str(project.id)

    def test_update_project(self, client, auth_headers, project):
        rv = client.put(
            f"/api/projects/{project.id}",
            json={"name": "Renamed", "alert": False},
            headers=auth_headers,
        )
        assert rv.status_code == 200
        assert rv.get_json()["name"] == "Renamed"

    def test_delete_project(self, client, auth_headers, project):
        rv = client.delete(f"/api/projects/{project.id}", headers=auth_headers)
        assert rv.status_code == 200

        rv2 = client.get(f"/api/projects/{project.id}", headers=auth_headers)
        assert rv2.status_code == 404

    def test_get_nonexistent_project(self, client, auth_headers):
        rv = client.get("/api/projects/000000000000000000000000", headers=auth_headers)
        assert rv.status_code == 404


class TestProjectMembers:
    def test_list_members(self, client, auth_headers, project):
        rv = client.get(f"/api/projects/{project.id}/members", headers=auth_headers)
        assert rv.status_code == 200
        members = rv.get_json()
        assert any(m["role"] == "owner" for m in members)

    def test_add_member(self, client, auth_headers, project, regular_user):
        rv = client.post(
            f"/api/projects/{project.id}/members",
            json={"user_id": str(regular_user.id), "role": "task_runner"},
            headers=auth_headers,
        )
        assert rv.status_code == 201
        assert rv.get_json()["role"] == "task_runner"

    def test_add_duplicate_member_fails(self, client, auth_headers, project, regular_user):
        client.post(
            f"/api/projects/{project.id}/members",
            json={"user_id": str(regular_user.id), "role": "guest"},
            headers=auth_headers,
        )
        rv = client.post(
            f"/api/projects/{project.id}/members",
            json={"user_id": str(regular_user.id), "role": "manager"},
            headers=auth_headers,
        )
        assert rv.status_code == 409

    def test_remove_member(self, client, auth_headers, project, regular_user):
        rv = client.post(
            f"/api/projects/{project.id}/members",
            json={"user_id": str(regular_user.id), "role": "guest"},
            headers=auth_headers,
        )
        member_id = rv.get_json()["id"]

        rv2 = client.delete(f"/api/projects/{project.id}/members/{member_id}", headers=auth_headers)
        assert rv2.status_code == 200


class TestProjectRBAC:
    def test_guest_cannot_delete_project(self, client, project, regular_user):
        from app.models.project import ProjectMember
        ProjectMember(project=project, user=regular_user, role="guest").save()

        from app.services.auth_service import create_access_token
        token = create_access_token(str(regular_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        rv = client.delete(f"/api/projects/{project.id}", headers=headers)
        assert rv.status_code == 403

    def test_non_member_cannot_access_project(self, client, user_headers, project):
        rv = client.get(f"/api/projects/{project.id}", headers=user_headers)
        assert rv.status_code == 403

    def test_task_runner_can_read_templates(self, client, project, regular_user):
        from app.models.project import ProjectMember
        from app.services.auth_service import create_access_token
        ProjectMember(project=project, user=regular_user, role="task_runner").save()
        token = create_access_token(str(regular_user.id))
        rv = client.get(
            f"/api/projects/{project.id}/templates",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rv.status_code == 200

    def test_task_runner_cannot_create_template(self, client, project, regular_user):
        from app.models.project import ProjectMember
        from app.services.auth_service import create_access_token
        ProjectMember(project=project, user=regular_user, role="task_runner").save()
        token = create_access_token(str(regular_user.id))
        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "T", "app": "bash"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rv.status_code == 403
