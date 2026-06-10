"""Tests for /api/projects/<id>/tasks and task service."""
from __future__ import annotations

import pytest


@pytest.fixture
def bash_template(client, auth_headers, project):
    rv = client.post(
        f"/api/projects/{project.id}/templates",
        json={"name": "Hello Bash", "app": "bash", "playbook": "hello.sh"},
        headers=auth_headers,
    )
    return rv.get_json()


class TestTaskStart:
    def test_start_task(self, client, auth_headers, project, bash_template):
        rv = client.post(
            f"/api/projects/{project.id}/tasks/{bash_template['id']}/start",
            json={},
            headers=auth_headers,
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["status"] in ("waiting", "success", "error")
        assert data["template_id"] == bash_template["id"]

    def test_list_tasks(self, client, auth_headers, project, bash_template):
        client.post(
            f"/api/projects/{project.id}/tasks/{bash_template['id']}/start",
            json={},
            headers=auth_headers,
        )
        rv = client.get(f"/api/projects/{project.id}/tasks", headers=auth_headers)
        assert rv.status_code == 200
        assert len(rv.get_json()["items"]) == 1

    def test_get_task(self, client, auth_headers, project, bash_template):
        rv = client.post(
            f"/api/projects/{project.id}/tasks/{bash_template['id']}/start",
            json={},
            headers=auth_headers,
        )
        task_id = rv.get_json()["id"]
        rv2 = client.get(f"/api/projects/{project.id}/tasks/{task_id}", headers=auth_headers)
        assert rv2.status_code == 200
        assert rv2.get_json()["id"] == task_id

    def test_stop_waiting_task(self, client, auth_headers, project, bash_template):
        from app.models.task import Task
        from app.models.template import Template
        from app.services.task_service import create_task

        tmpl = Template.objects.get(id=bash_template["id"])
        task = create_task(tmpl)  # create but don't enqueue → stays waiting

        rv = client.post(
            f"/api/projects/{project.id}/tasks/{task.id}/stop",
            headers=auth_headers,
        )
        assert rv.status_code == 200
        task.reload()
        assert task.status == "stopped"

    def test_get_task_log(self, client, auth_headers, project, bash_template):
        rv = client.post(
            f"/api/projects/{project.id}/tasks/{bash_template['id']}/start",
            json={},
            headers=auth_headers,
        )
        task_id = rv.get_json()["id"]
        rv2 = client.get(f"/api/projects/{project.id}/tasks/{task_id}/log", headers=auth_headers)
        assert rv2.status_code == 200
        assert "output" in rv2.get_json()

    def test_guest_cannot_start_task(self, client, project, bash_template, regular_user):
        from app.models.project import ProjectMember
        from app.services.auth_service import create_access_token
        ProjectMember(project=project, user=regular_user, role="guest").save()
        token = create_access_token(str(regular_user.id))
        rv = client.post(
            f"/api/projects/{project.id}/tasks/{bash_template['id']}/start",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rv.status_code == 403


class TestTaskService:
    def test_create_task_waiting(self, app, project):
        from app.models.template import Template
        from app.models.project import Project
        from app.services.task_service import create_task

        tmpl = Template(project=project, name="T", app="bash").save()
        task = create_task(tmpl)
        assert task.status == "waiting"
        assert str(task.project.id) == str(project.id)

    def test_stop_waiting_task_directly(self, app, project):
        from app.models.template import Template
        from app.services.task_service import create_task, stop_task

        tmpl = Template(project=project, name="T2", app="bash").save()
        task = create_task(tmpl)
        stop_task(task)
        task.reload()
        assert task.status == "stopped"
