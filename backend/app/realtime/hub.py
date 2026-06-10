from __future__ import annotations

from app.extensions import socketio
from flask_socketio import join_room, leave_room, disconnect
from flask import request

from app.services.rbac import load_user_from_token, user_can_access_project

# Per-connection authenticated identity, keyed by socket session id (sid).
# Events for a given connection are always handled by the worker that owns
# the connection, so a process-local mapping is sufficient.
_sid_users: dict[str, object] = {}


def _current_user():
    return _sid_users.get(request.sid)


@socketio.on("connect")
def on_connect(auth):
    """Authenticate the socket during the handshake.

    The client passes its JWT in the Socket.IO ``auth`` payload
    (``io('/', { auth: { token } })``). An unauthenticated or invalid
    token rejects the connection.
    """
    token = (auth or {}).get("token", "") if isinstance(auth, dict) else ""
    if not token:
        return False
    user, _ = load_user_from_token(token)
    if user is None:
        return False
    _sid_users[request.sid] = user
    return True


@socketio.on("disconnect")
def on_disconnect():
    _sid_users.pop(request.sid, None)


@socketio.on("subscribe_task")
def on_subscribe_task(data):
    task_id = data.get("task_id")
    if not task_id:
        return
    user = _current_user()
    if user is None:
        disconnect()
        return
    # Resolve the task's project and authorize membership before joining.
    from app.models.task import Task

    try:
        task = Task.objects.get(id=task_id)
    except (Task.DoesNotExist, Exception):
        return
    if not user_can_access_project(user, str(task.project.id)):
        return
    join_room(f"task:{task_id}")


@socketio.on("unsubscribe_task")
def on_unsubscribe_task(data):
    task_id = data.get("task_id")
    if task_id:
        leave_room(f"task:{task_id}")


@socketio.on("subscribe_project")
def on_subscribe_project(data):
    project_id = data.get("project_id")
    if not project_id:
        return
    user = _current_user()
    if user is None:
        disconnect()
        return
    if not user_can_access_project(user, str(project_id)):
        return
    join_room(f"project:{project_id}")


def emit_task_log(task_id: str, line: str) -> None:
    socketio.emit("task_output", {"task_id": task_id, "line": line}, room=f"task:{task_id}")


def emit_task_status(task_id: str, status: str) -> None:
    socketio.emit(
        "task_status",
        {"task_id": task_id, "status": status},
        room=f"task:{task_id}",
    )
