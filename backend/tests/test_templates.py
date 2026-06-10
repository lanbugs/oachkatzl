"""Tests for /api/projects/<id>/templates."""
from __future__ import annotations


class TestTemplates:
    def test_create_bash_template(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "Deploy Script", "app": "bash", "playbook": "deploy.sh"},
            headers=auth_headers,
        )
        assert rv.status_code == 201
        data = rv.get_json()
        assert data["app"] == "bash"
        assert data["name"] == "Deploy Script"

    def test_create_ansible_template(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "Playbook Run", "app": "ansible", "playbook": "site.yml"},
            headers=auth_headers,
        )
        assert rv.status_code == 201
        assert rv.get_json()["app"] == "ansible"

    def test_create_python_template(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "Python Job", "app": "python", "playbook": "main.py"},
            headers=auth_headers,
        )
        assert rv.status_code == 201

    def test_create_template_invalid_app(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "Bad", "app": "terraform"},
            headers=auth_headers,
        )
        assert rv.status_code == 400

    def test_list_templates(self, client, auth_headers, project):
        client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "T1", "app": "bash"},
            headers=auth_headers,
        )
        rv = client.get(f"/api/projects/{project.id}/templates", headers=auth_headers)
        assert rv.status_code == 200
        assert len(rv.get_json()["items"]) == 1

    def test_get_template(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "T", "app": "bash"},
            headers=auth_headers,
        )
        tmpl_id = rv.get_json()["id"]
        rv2 = client.get(f"/api/projects/{project.id}/templates/{tmpl_id}", headers=auth_headers)
        assert rv2.status_code == 200
        assert rv2.get_json()["id"] == tmpl_id

    def test_update_template(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "Old", "app": "bash"},
            headers=auth_headers,
        )
        tmpl_id = rv.get_json()["id"]
        rv2 = client.put(
            f"/api/projects/{project.id}/templates/{tmpl_id}",
            json={"name": "New", "app": "python"},
            headers=auth_headers,
        )
        assert rv2.status_code == 200
        assert rv2.get_json()["name"] == "New"

    def test_delete_template(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={"name": "T", "app": "bash"},
            headers=auth_headers,
        )
        tmpl_id = rv.get_json()["id"]
        rv2 = client.delete(f"/api/projects/{project.id}/templates/{tmpl_id}", headers=auth_headers)
        assert rv2.status_code == 200

    def test_template_with_survey_vars(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/templates",
            json={
                "name": "Survey Template",
                "app": "bash",
                "survey_vars": [
                    {"name": "env", "title": "Environment", "type": "enum",
                     "values": ["staging", "prod"], "required": True},
                    {"name": "version", "title": "Version", "type": "string"},
                ],
            },
            headers=auth_headers,
        )
        assert rv.status_code == 201
        svars = rv.get_json()["survey_vars"]
        assert len(svars) == 2
        assert svars[0]["name"] == "env"
        assert svars[0]["values"] == ["staging", "prod"]
