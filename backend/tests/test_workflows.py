"""Tests for the survey workflow node (/workflow-runs/<id>/survey[-submit])."""
from __future__ import annotations

import json


def _make_paused_survey_run(project, input_schema: dict):
    from app.models.workflow import WorkflowTemplate, WorkflowNode
    from app.models.workflow_run import WorkflowRun, WorkflowNodeRun
    from app.models.artifact import ArtifactCache
    from app.services.artifact_service import create_artifact_run, store_json

    wf = WorkflowTemplate(
        project=project,
        name="Survey Workflow",
        nodes=[
            WorkflowNode(
                node_id="n1",
                node_type="survey",
                action_config={
                    "input_artifact_name": "schema_in",
                    "output_artifact_name": "answers_out",
                },
            )
        ],
    ).save()

    run = WorkflowRun(
        project=project,
        workflow=wf,
        status="waiting_approval",
        pending_approval_node_id="n1",
        node_runs=[WorkflowNodeRun(node_id="n1", status="waiting_approval")],
    ).save()

    cache = ArtifactCache(project=project, name="cache1").save()
    artifact_run, _token = create_artifact_run(cache=cache, workflow_run=run)
    run.artifact_run = artifact_run
    run.save()

    store_json(artifact_run, "schema_in", input_schema)
    return wf, run, artifact_run


class TestSurveyWorkflowNode:
    def test_create_workflow_with_survey_node(self, client, auth_headers, project):
        rv = client.post(
            f"/api/projects/{project.id}/workflows/",
            json={
                "name": "WF",
                "nodes": [
                    {
                        "node_id": "n1",
                        "node_type": "survey",
                        "label": "Collect input",
                        "action_config": {
                            "input_artifact_name": "schema_in",
                            "output_artifact_name": "answers_out",
                        },
                    }
                ],
            },
            headers=auth_headers,
        )
        assert rv.status_code == 201
        node = rv.get_json()["nodes"][0]
        assert node["node_type"] == "survey"
        assert node["action_config"]["input_artifact_name"] == "schema_in"
        assert node["action_config"]["output_artifact_name"] == "answers_out"

    def test_get_survey_schema(self, client, auth_headers, project):
        schema = {
            "title": "Deployment",
            "fields": [
                {"name": "env", "type": "enum", "options": [{"value": "dev", "label": "Dev"}]},
            ],
        }
        _wf, run, _ar = _make_paused_survey_run(project, schema)

        rv = client.get(
            f"/api/projects/{project.id}/workflow-runs/{run.id}/survey",
            headers=auth_headers,
        )
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["node_id"] == "n1"
        assert data["output_artifact_name"] == "answers_out"
        assert data["schema"]["title"] == "Deployment"
        assert data["schema"]["fields"][0]["name"] == "env"

    def test_get_survey_schema_requires_waiting_approval(self, client, auth_headers, project):
        _wf, run, _ar = _make_paused_survey_run(project, {"fields": []})
        run.status = "running"
        run.save()

        rv = client.get(
            f"/api/projects/{project.id}/workflow-runs/{run.id}/survey",
            headers=auth_headers,
        )
        assert rv.status_code == 400

    def test_submit_survey_stores_artifact_and_resumes(self, client, auth_headers, project):
        from app.models.artifact import Artifact
        from app.models.workflow_run import WorkflowRun

        schema = {"title": "Deployment", "fields": [{"name": "env", "type": "string"}]}
        _wf, run, artifact_run = _make_paused_survey_run(project, schema)

        rv = client.post(
            f"/api/projects/{project.id}/workflow-runs/{run.id}/survey-submit",
            json={"answers": {"env": "prod"}},
            headers=auth_headers,
        )
        assert rv.status_code == 200

        art = Artifact.objects(run=artifact_run, name="answers_out", artifact_type="json").first()
        assert art is not None
        assert json.loads(art.json_data) == {"env": "prod"}

        # Single-node workflow with no successors resolves to "success" once
        # advance_workflow (run synchronously via CELERY_TASK_ALWAYS_EAGER) finishes.
        reloaded = WorkflowRun.objects.get(id=run.id)
        assert reloaded.status == "success"
        assert reloaded.pending_approval_node_id == ""
        node_run = next(nr for nr in reloaded.node_runs if nr.node_id == "n1")
        assert node_run.status == "success"

    def test_submit_survey_requires_pending_survey(self, client, auth_headers, project):
        _wf, run, _ar = _make_paused_survey_run(project, {"fields": []})
        run.status = "running"
        run.pending_approval_node_id = ""
        run.save()

        rv = client.post(
            f"/api/projects/{project.id}/workflow-runs/{run.id}/survey-submit",
            json={"answers": {}},
            headers=auth_headers,
        )
        assert rv.status_code == 400
