from __future__ import annotations

from mongoengine import BooleanField, Document, ReferenceField, StringField, NULLIFY

from app.models.project import Project

CHANNELS = ("email", "slack", "telegram", "teams", "rocketchat", "dingtalk", "gotify")
SCOPES = ("global", "project")


class NotificationSetting(Document):
    meta = {"collection": "notification_settings"}

    scope = StringField(choices=SCOPES, default="global")
    project = ReferenceField(Project, null=True, reverse_delete_rule=NULLIFY)
    channel = StringField(choices=CHANNELS, required=True)
    config = StringField(default="{}")   # JSON: webhook url, token, etc.
    on_success = BooleanField(default=False)
    on_failure = BooleanField(default=True)
