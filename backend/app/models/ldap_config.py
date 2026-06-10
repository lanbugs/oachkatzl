from __future__ import annotations

from mongoengine import (
    BooleanField,
    CASCADE,
    Document,
    ListField,
    ReferenceField,
    StringField,
)

from app.models.project import ROLES


class LdapConfig(Document):
    """Singleton LDAP/AD configuration (always use .objects.first())."""

    meta = {"collection": "ldap_config"}

    enabled       = BooleanField(default=False)
    server_url    = StringField(default="")   # ldap://dc.corp.local:389  or  ldaps://…
    use_tls       = BooleanField(default=False)  # STARTTLS
    use_ssl       = BooleanField(default=False)  # ldaps://
    bind_dn       = StringField(default="")   # CN=svc-oachkatzl,OU=ServiceAccounts,DC=corp,DC=local
    bind_password_enc = StringField(default="")  # Fernet-encrypted
    base_dn       = StringField(default="")   # DC=corp,DC=local
    user_search_filter = StringField(default="(sAMAccountName={username})")
    group_membership_attr = StringField(default="memberOf")
    follow_nested_groups  = BooleanField(default=False)
    # Attribute mapping
    attr_email        = StringField(default="mail")
    attr_display_name = StringField(default="displayName")
    attr_uid          = StringField(default="objectGUID")
    # Global admin groups — members of these AD groups become system admins
    admin_groups      = ListField(StringField(), default=list)  # stored lowercase


class LdapGroupMapping(Document):
    """Maps a single AD group DN to a project role."""

    meta = {
        "collection": "ldap_group_mappings",
        "indexes": ["group_dn", "project"],
    }

    # Stored lowercase for case-insensitive matching
    group_dn = StringField(required=True)
    project  = ReferenceField("Project", required=True, reverse_delete_rule=CASCADE)
    role     = StringField(required=True, choices=ROLES)


class LdapUserMapping(Document):
    """Maps a specific LDAP username directly to a project role (bypasses group logic)."""

    meta = {
        "collection": "ldap_user_mappings",
        "indexes": [{"fields": ["ldap_username", "project"], "unique": True}],
    }

    # Stored lowercase — matched against User.username for ldap users
    ldap_username = StringField(required=True)
    project       = ReferenceField("Project", required=True, reverse_delete_rule=CASCADE)
    role          = StringField(required=True, choices=ROLES)
