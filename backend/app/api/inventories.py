from __future__ import annotations

from apiflask import APIBlueprint, HTTPError
from apiflask.fields import String
from apiflask.schemas import Schema
from flask import g

from app.services.rbac import require_project_role

bp = APIBlueprint("inventories", __name__, url_prefix="/api/projects/<project_id>/inventories")

INVENTORY_TYPES = ("static", "static-yaml", "file", "none")


class InventoryIn(Schema):
    name = String(required=True)
    type = String(required=True)
    inventory = String(load_default="")
    inventory_file = String(load_default="")
    ssh_key_id = String(load_default=None)
    become_key_id = String(load_default=None)


class InventoryOut(Schema):
    id = String()
    name = String()
    type = String()
    inventory = String()
    inventory_file = String()
    ssh_key_id = String(dump_default=None)
    become_key_id = String(dump_default=None)
    created_at = String()


def _out(inv) -> dict:
    return {
        "id": str(inv.id),
        "name": inv.name,
        "type": inv.type,
        "inventory": inv.inventory,
        "inventory_file": inv.inventory_file,
        "ssh_key_id": str(inv.ssh_key.id) if inv.ssh_key else None,
        "become_key_id": str(inv.become_key.id) if inv.become_key else None,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


@bp.get("/")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(InventoryOut(many=True))
def list_inventories(project_id):
    from app.models.inventory import Inventory
    return [_out(i) for i in Inventory.objects(project=g.project)]


@bp.post("/")
@require_project_role("owner", "manager")
@bp.input(InventoryIn, arg_name="body")
@bp.output(InventoryOut, status_code=201)
def create_inventory(project_id, body):
    from app.models.inventory import Inventory
    from app.models.access_key import AccessKey

    def _key(kid):
        if not kid:
            return None
        try:
            return AccessKey.objects.get(id=kid, project=g.project)
        except AccessKey.DoesNotExist:
            raise HTTPError(404, f"Key {kid} not found")

    inv = Inventory(
        project=g.project,
        name=body["name"],
        type=body["type"],
        inventory=body.get("inventory", ""),
        inventory_file=body.get("inventory_file", ""),
        ssh_key=_key(body.get("ssh_key_id")),
        become_key=_key(body.get("become_key_id")),
    ).save()
    return _out(inv)


@bp.get("/<inv_id>")
@require_project_role("owner", "manager", "task_runner", "guest")
@bp.output(InventoryOut)
def get_inventory(project_id, inv_id):
    from app.models.inventory import Inventory
    try:
        return _out(Inventory.objects.get(id=inv_id, project=g.project))
    except Inventory.DoesNotExist:
        raise HTTPError(404, "Inventory not found")


@bp.put("/<inv_id>")
@require_project_role("owner", "manager")
@bp.input(InventoryIn, arg_name="body")
@bp.output(InventoryOut)
def update_inventory(project_id, inv_id, body):
    from app.models.inventory import Inventory
    from app.models.access_key import AccessKey

    def _key(kid):
        if not kid:
            return None
        try:
            return AccessKey.objects.get(id=kid, project=g.project)
        except AccessKey.DoesNotExist:
            raise HTTPError(404, f"Key {kid} not found")

    try:
        inv = Inventory.objects.get(id=inv_id, project=g.project)
    except Inventory.DoesNotExist:
        raise HTTPError(404, "Inventory not found")

    inv.name = body["name"]
    inv.type = body["type"]
    inv.inventory = body.get("inventory", inv.inventory)
    inv.inventory_file = body.get("inventory_file", inv.inventory_file)
    inv.ssh_key = _key(body.get("ssh_key_id"))
    inv.become_key = _key(body.get("become_key_id"))
    inv.save()
    return _out(inv)


@bp.delete("/<inv_id>")
@require_project_role("owner", "manager")
def delete_inventory(project_id, inv_id):
    from app.models.inventory import Inventory
    try:
        Inventory.objects.get(id=inv_id, project=g.project).delete()
    except Inventory.DoesNotExist:
        raise HTTPError(404, "Inventory not found")
    return {"message": "Deleted"}, 200
