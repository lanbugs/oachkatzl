from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import String
from apiflask.schemas import Schema
from flask import g

from app.services.rbac import require_project_role

bp = APIBlueprint("repositories", __name__, url_prefix="/api/projects/<project_id>/repositories")


class RepoIn(Schema):
    name = String(required=True)
    git_url = String(required=True)
    git_branch = String(load_default="main")
    ssh_key_id = String(load_default=None)


class RepoOut(Schema):
    id = String()
    name = String()
    git_url = String()
    git_branch = String()
    ssh_key_id = String(dump_default=None)
    created_at = String()


def _out(r) -> dict:
    return {
        "id": str(r.id),
        "name": r.name,
        "git_url": r.git_url,
        "git_branch": r.git_branch,
        "ssh_key_id": str(r.ssh_key.id) if r.ssh_key else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(RepoOut(many=True))
def list_repos(project_id):
    from app.models.repository import Repository
    return [_out(r) for r in Repository.objects(project=g.project)]


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(RepoIn, arg_name="body")
@bp.output(RepoOut, status_code=201)
def create_repo(project_id, body):
    from app.models.repository import Repository
    from app.models.access_key import AccessKey
    ssh_key = None
    if body.get("ssh_key_id"):
        try:
            ssh_key = AccessKey.objects.get(id=body["ssh_key_id"], project=g.project)
        except AccessKey.DoesNotExist:
            raise HTTPError(404, "SSH key not found")
    r = Repository(
        project=g.project, name=body["name"],
        git_url=body["git_url"], git_branch=body.get("git_branch", "main"),
        ssh_key=ssh_key,
    ).save()
    return _out(r)


@bp.get("/<repo_id>")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(RepoOut)
def get_repo(project_id, repo_id):
    from app.models.repository import Repository
    try:
        return _out(Repository.objects.get(id=repo_id, project=g.project))
    except Repository.DoesNotExist:
        raise HTTPError(404, "Repository not found")


@bp.put("/<repo_id>")
@require_project_role("owner", "manager")
@bp.input(RepoIn, arg_name="body")
@bp.output(RepoOut)
def update_repo(project_id, repo_id, body):
    from app.models.repository import Repository
    from app.models.access_key import AccessKey
    try:
        r = Repository.objects.get(id=repo_id, project=g.project)
    except Repository.DoesNotExist:
        raise HTTPError(404, "Repository not found")
    r.name = body["name"]
    r.git_url = body["git_url"]
    r.git_branch = body.get("git_branch", r.git_branch)
    if body.get("ssh_key_id"):
        try:
            r.ssh_key = AccessKey.objects.get(id=body["ssh_key_id"], project=g.project)
        except AccessKey.DoesNotExist:
            raise HTTPError(404, "SSH key not found")
    else:
        r.ssh_key = None
    r.save()
    return _out(r)


@bp.delete("/<repo_id>")
@require_project_role("owner", "manager")
def delete_repo(project_id, repo_id):
    from app.models.repository import Repository
    try:
        Repository.objects.get(id=repo_id, project=g.project).delete()
    except Repository.DoesNotExist:
        raise HTTPError(404, "Repository not found")
    return {"message": "Deleted"}, 200
