from apiflask.fields import Boolean, List, String
from apiflask.schemas import Schema


class CredentialTypeIn(Schema):
    name        = String(required=True)
    description = String(load_default="")
    inputs      = String(load_default="[]")    # JSON string
    injectors   = String(load_default="{}")    # JSON string


class CredentialTypeOut(Schema):
    id          = String()
    name        = String()
    description = String()
    inputs      = String()
    injectors   = String()
    created_at  = String()


class CredentialIn(Schema):
    name               = String(required=True)
    credential_type_id = String(required=True)
    # Field values keyed by field id — only provided on create/update
    # Missing keys → keep existing encrypted value
    inputs             = String(load_default="{}")   # JSON: {field_id: value}


class CredentialOut(Schema):
    id                 = String()
    name               = String()
    credential_type_id = String()
    credential_type_name = String(dump_default="")
    # IDs of fields that have a value stored (secrets never returned)
    filled_fields      = List(String())
    created_at         = String()
