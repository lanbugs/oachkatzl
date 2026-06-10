from __future__ import annotations

from mongoengine import Document, StringField


class Option(Document):
    meta = {"collection": "options"}

    key = StringField(required=True, unique=True)
    value = StringField(default="")   # JSON-encoded value
