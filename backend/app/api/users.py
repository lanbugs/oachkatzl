from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import Boolean, String
from apiflask.schemas import Schema
from marshmallow import validate

from app.services.rbac import require_admin, require_auth
from flask import g

bp = APIBlueprint("users", __name__, url_prefix="/api/users")


class UserCreateIn(Schema):
    username = String(required=True)
    email = String(required=True)
    name = String(load_default="")
    password = String(required=True, validate=validate.Length(min=8))
    is_admin = Boolean(load_default=False)


class UserUpdateIn(Schema):
    email = String(load_default=None)
    name = String(load_default=None)
    password = String(load_default=None)
    is_admin = Boolean(load_default=None)
    active = Boolean(load_default=None)


class UserOut(Schema):
    id = String()
    username = String()
    email = String()
    name = String()
    is_admin = Boolean()
    active = Boolean()
    auth_provider = String()
    totp_enabled = Boolean()
    created_at = String()


def _user_out(u) -> dict:
    return {
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "name": u.name,
        "is_admin": u.is_admin,
        "active": u.active,
        "auth_provider": u.auth_provider,
        "totp_enabled": u.totp_enabled,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@bp.get("/")
@require_admin
@bp.output(UserOut(many=True))
def list_users():
    from app.models.user import User
    return [_user_out(u) for u in User.objects.all()]


@bp.post("/")
@require_admin
@bp.input(UserCreateIn, arg_name="body")
@bp.output(UserOut, status_code=201)
def create_user(body):
    from app.models.user import User
    from app.services.auth_service import hash_password

    if User.objects(username=body["username"]).first():
        raise HTTPError(409, "Username already exists")
    if User.objects(email=body["email"]).first():
        raise HTTPError(409, "Email already exists")

    user = User(
        username=body["username"],
        email=body["email"],
        name=body.get("name", ""),
        password_hash=hash_password(body["password"]),
        is_admin=body.get("is_admin", False),
        active=True,
    ).save()
    return _user_out(user)


@bp.get("/<user_id>")
@require_auth
@bp.output(UserOut)
def get_user(user_id):
    from app.models.user import User
    if not g.current_user.is_admin and str(g.current_user.id) != user_id:
        raise HTTPError(403, "Forbidden")
    try:
        return _user_out(User.objects.get(id=user_id))
    except User.DoesNotExist:
        raise HTTPError(404, "User not found")


@bp.put("/<user_id>")
@require_admin
@bp.input(UserUpdateIn, arg_name="body")
@bp.output(UserOut)
def update_user(user_id, body):
    from app.models.user import User
    from app.services.auth_service import hash_password
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise HTTPError(404, "User not found")

    if body.get("email") is not None:
        user.email = body["email"]
    if body.get("name") is not None:
        user.name = body["name"]
    if body.get("password") is not None:
        user.password_hash = hash_password(body["password"])
    if body.get("is_admin") is not None:
        user.is_admin = body["is_admin"]
    if body.get("active") is not None:
        user.active = body["active"]
    user.save()
    return _user_out(user)


@bp.delete("/<user_id>")
@require_admin
def delete_user(user_id):
    from app.models.user import User
    try:
        User.objects.get(id=user_id).delete()
    except User.DoesNotExist:
        raise HTTPError(404, "User not found")
    return {"message": "Deleted"}, 200
