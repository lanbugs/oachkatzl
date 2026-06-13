from __future__ import annotations

import datetime

from apiflask import APIBlueprint
from flask import g

from app.services.rbac import require_auth

bp = APIBlueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("/task-stats")
@require_auth
def task_stats():
    """Return per-day success/error task counts for the last 7 days."""
    from app.models.task import Task
    from app.models.project import ProjectMember

    now = datetime.datetime.utcnow()
    seven_days_ago = now - datetime.timedelta(days=7)

    # Last 7 days in chronological order (today is index 6)
    days = [
        (now - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(6, -1, -1)
    ]

    match: dict = {
        "created_at": {"$gte": seven_days_ago},
        "status": {"$in": ["success", "error"]},
    }

    if not g.current_user.is_admin:
        memberships = ProjectMember.objects(user=g.current_user).only("project")
        project_ids = [m.project.id for m in memberships]
        match["project"] = {"$in": project_ids}

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": {
                    "date": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at",
                        }
                    },
                    "status": "$status",
                },
                "count": {"$sum": 1},
            }
        },
    ]

    counts: dict[str, dict[str, int]] = {d: {"success": 0, "error": 0} for d in days}
    for row in Task._get_collection().aggregate(pipeline):
        date = row["_id"]["date"]
        status = row["_id"]["status"]
        if date in counts and status in counts[date]:
            counts[date][status] = row["count"]

    return [
        {"date": d, "success": counts[d]["success"], "error": counts[d]["error"]}
        for d in days
    ], 200
