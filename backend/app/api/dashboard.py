from __future__ import annotations

import datetime
from collections import defaultdict

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


@bp.get("/worker-status")
@require_auth
def worker_status():
    """Return live worker pool status via Celery inspect."""
    from app.celery_app import celery
    from app.models.worker_pool import WorkerPool

    # Seed known pools from DB so offline pools still appear with 0 workers
    pools: dict[str, dict] = {
        "celery": {
            "queue": "celery",
            "name": "Default",
            "workers_total": 0,
            "capacity": 0,
            "workers_busy": 0,
            "tasks_active": 0,
        }
    }
    for wp in WorkerPool.objects(active=True).order_by("name"):
        pools[wp.slug] = {
            "queue": wp.slug,
            "name": wp.name,
            "workers_total": 0,
            "capacity": 0,
            "workers_busy": 0,
            "tasks_active": 0,
        }

    try:
        insp = celery.control.inspect(timeout=1.5)
        queues_result: dict = insp.active_queues() or {}
        active_result: dict = insp.active() or {}
        stats_result:  dict = insp.stats()        or {}
    except Exception:
        queues_result = {}
        active_result = {}
        stats_result  = {}

    # Capacity per worker: pool.max-concurrency from stats()
    worker_capacity: dict[str, int] = {}
    for worker_name, wstats in stats_result.items():
        pool = wstats.get("pool", {})
        cap = pool.get("max-concurrency") or pool.get("processes") or 1
        try:
            worker_capacity[worker_name] = int(cap)
        except (TypeError, ValueError):
            worker_capacity[worker_name] = 1

    # Count workers and capacity per queue
    for worker_name, worker_queues in queues_result.items():
        for q in worker_queues or []:
            qname = q.get("name", "celery")
            if qname not in pools:
                pools[qname] = {
                    "queue": qname,
                    "name": qname,
                    "workers_total": 0,
                    "capacity": 0,
                    "workers_busy": 0,
                    "tasks_active": 0,
                }
            pools[qname]["workers_total"] += 1
            pools[qname]["capacity"] += worker_capacity.get(worker_name, 1)

    # Count active tasks and busy workers per queue
    busy_per_queue: dict[str, set] = defaultdict(set)
    for worker_name, tasks in active_result.items():
        for task in tasks or []:
            rk = task.get("delivery_info", {}).get("routing_key", "celery")
            if rk in pools:
                pools[rk]["tasks_active"] += 1
                busy_per_queue[rk].add(worker_name)

    for qname, workers in busy_per_queue.items():
        if qname in pools:
            pools[qname]["workers_busy"] = len(workers)

    # Default pool first, rest alphabetically
    result = sorted(pools.values(), key=lambda p: (p["queue"] != "celery", p["queue"]))
    return {"pools": result}, 200
