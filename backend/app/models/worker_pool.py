from __future__ import annotations

import datetime

from mongoengine import BooleanField, DateTimeField, Document, StringField


class WorkerPool(Document):
    """Admin-defined named Celery queue slot for custom worker images."""

    meta = {"collection": "worker_pools", "indexes": ["slug"]}

    slug = StringField(required=True, unique=True, max_length=64)
    name = StringField(required=True, max_length=255)
    description = StringField(default="")
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
