from __future__ import annotations

import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    Document,
    IntField,
    ListField,
    StringField,
)

RUNNER_STATUSES = ("active", "offline")


class Runner(Document):
    meta = {"collection": "runners"}

    name = StringField(required=True, max_length=255)
    token_hash = StringField(required=True, unique=True)
    tags = ListField(StringField())
    status = StringField(choices=RUNNER_STATUSES, default="offline")
    last_seen = DateTimeField(default=datetime.datetime.utcnow)
    max_parallel_tasks = IntField(default=1)
    webhook = StringField(default="")
    active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
