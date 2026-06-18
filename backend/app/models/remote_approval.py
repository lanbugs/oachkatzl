from __future__ import annotations

import datetime
import secrets

from mongoengine import DateTimeField, Document, StringField


class RemoteApprovalToken(Document):
    """One token per email recipient for a remote_approval workflow node."""

    meta = {
        "collection": "remote_approval_tokens",
        "indexes": ["token", ("workflow_run_id", "node_id")],
    }

    workflow_run_id = StringField(required=True)
    node_id = StringField(required=True)
    email = StringField(required=True)
    token = StringField(required=True, unique=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    @classmethod
    def generate(cls, workflow_run_id: str, node_id: str, email: str) -> "RemoteApprovalToken":
        obj = cls(
            workflow_run_id=workflow_run_id,
            node_id=node_id,
            email=email,
            token=secrets.token_urlsafe(32),
        )
        obj.save()
        return obj
