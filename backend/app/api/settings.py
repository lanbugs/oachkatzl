from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import String
from apiflask.schemas import Schema

from app.services.rbac import require_admin

bp = APIBlueprint("settings", __name__, url_prefix="/api/settings")

# Option keys whose values are stored encrypted and must never be returned in plaintext.
_SENSITIVE_OPTION_KEYS = {"SMTP_PASSWORD"}


class OptionIn(Schema):
    key = String(required=True)
    value = String(required=True)


class OptionOut(Schema):
    key = String()
    value = String()


def _mask_sensitive(key: str, stored_value: str) -> str:
    """Return '***' for sensitive keys that have a value set."""
    if key in _SENSITIVE_OPTION_KEYS:
        return "***" if stored_value else ""
    return stored_value


def _encrypt_if_sensitive(key: str, value: str) -> str:
    """Encrypt the value for sensitive keys before storing."""
    if key in _SENSITIVE_OPTION_KEYS and value and value != "***":
        from app.services.crypto import encrypt
        return encrypt(value)
    return value


@bp.get("/")
@require_admin
@bp.output(OptionOut(many=True))
def list_options():
    from app.models.option import Option
    return [
        {"key": o.key, "value": _mask_sensitive(o.key, o.value)}
        for o in Option.objects.all()
    ]


@bp.put("/")
@require_admin
@bp.input(OptionIn, arg_name="body")
@bp.output(OptionOut)
def set_option(body):
    from app.models.option import Option
    key = body["key"]
    value = _encrypt_if_sensitive(key, body["value"])
    opt = Option.objects(key=key).first()
    if opt:
        opt.value = value
        opt.save()
    else:
        opt = Option(key=key, value=value).save()
    return {"key": opt.key, "value": _mask_sensitive(opt.key, opt.value)}
