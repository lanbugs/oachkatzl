from __future__ import annotations

import hashlib
import hmac
import json

from flask import Request


def _get_value(source: str, key: str, request: Request) -> str | None:
    if source == "header":
        return request.headers.get(key)
    if source == "body":
        try:
            body = request.get_json(force=True, silent=True) or {}
            for part in key.split("."):
                body = body[part]
            return str(body)
        except (KeyError, TypeError):
            return None
    return None


def check_matchers(integration, request: Request) -> bool:
    for m in integration.matchers:
        val = _get_value(m.match_type, m.key, request)
        if m.method == "exists":
            if val is None:
                return False
        elif m.method == "equals":
            if val != m.value:
                return False
        elif m.method == "unequals":
            if val == m.value:
                return False
        elif m.method == "contains":
            if val is None or m.value not in val:
                return False
    return True


def extract_values(integration, request: Request) -> dict:
    result = {}
    for ev in integration.extract_values:
        val = _get_value(ev.value_source, ev.key, request)
        if val is not None:
            result[ev.variable] = val
    return result


def verify_auth(integration, request: Request) -> bool:
    from app.services.crypto import decrypt

    method = integration.auth_method
    if method == "none":
        return True
    if method == "token":
        header = integration.auth_header or "X-Token"
        expected = decrypt(integration.auth_secret)
        received = request.headers.get(header, "")
        return hmac.compare_digest(expected, received)
    if method == "hmac":
        header = integration.auth_header or "X-Hub-Signature-256"
        secret = decrypt(integration.auth_secret).encode()
        body = request.get_data()
        expected_sig = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
        received = request.headers.get(header, "")
        return hmac.compare_digest(expected_sig, received)
    return False
