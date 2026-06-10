"""Tests for integration_service (matcher, extractor, auth verification)."""
from __future__ import annotations

from unittest.mock import MagicMock


def _make_request(body: dict | None = None, headers: dict | None = None):
    """Build a minimal mock Flask request."""
    req = MagicMock()
    req.get_json.return_value = body or {}
    req.get_data.return_value = b""
    req.headers = MagicMock()
    req.headers.get = lambda k, d=None: (headers or {}).get(k, d)
    return req


class TestMatchers:
    def _make_integration(self, matchers):
        integ = MagicMock()
        integ.matchers = matchers
        return integ

    def test_equals_match(self):
        from app.services.integration_service import check_matchers
        m = MagicMock()
        m.match_type = "body"
        m.key = "action"
        m.method = "equals"
        m.value = "push"
        req = _make_request(body={"action": "push"})
        integ = self._make_integration([m])
        assert check_matchers(integ, req)

    def test_equals_no_match(self):
        from app.services.integration_service import check_matchers
        m = MagicMock()
        m.match_type = "body"
        m.key = "action"
        m.method = "equals"
        m.value = "push"
        req = _make_request(body={"action": "pull_request"})
        assert not check_matchers(self._make_integration([m]), req)

    def test_contains_match(self):
        from app.services.integration_service import check_matchers
        m = MagicMock()
        m.match_type = "body"
        m.key = "ref"
        m.method = "contains"
        m.value = "main"
        req = _make_request(body={"ref": "refs/heads/main"})
        assert check_matchers(self._make_integration([m]), req)

    def test_exists_match(self):
        from app.services.integration_service import check_matchers
        m = MagicMock()
        m.match_type = "header"
        m.key = "X-GitHub-Event"
        m.method = "exists"
        m.value = ""
        req = _make_request(headers={"X-GitHub-Event": "push"})
        assert check_matchers(self._make_integration([m]), req)

    def test_exists_no_match(self):
        from app.services.integration_service import check_matchers
        m = MagicMock()
        m.match_type = "header"
        m.key = "X-Missing-Header"
        m.method = "exists"
        m.value = ""
        req = _make_request()
        assert not check_matchers(self._make_integration([m]), req)

    def test_no_matchers_always_passes(self):
        from app.services.integration_service import check_matchers
        req = _make_request()
        assert check_matchers(self._make_integration([]), req)


class TestExtractValues:
    def test_extract_body_value(self):
        from app.services.integration_service import extract_values
        ev = MagicMock()
        ev.value_source = "body"
        ev.key = "ref"
        ev.variable = "branch"
        ev.variable_type = "string"
        integ = MagicMock()
        integ.extract_values = [ev]
        req = _make_request(body={"ref": "refs/heads/main"})
        result = extract_values(integ, req)
        assert result == {"branch": "refs/heads/main"}

    def test_extract_header_value(self):
        from app.services.integration_service import extract_values
        ev = MagicMock()
        ev.value_source = "header"
        ev.key = "X-Event-Type"
        ev.variable = "event"
        ev.variable_type = "string"
        integ = MagicMock()
        integ.extract_values = [ev]
        req = _make_request(headers={"X-Event-Type": "push"})
        result = extract_values(integ, req)
        assert result == {"event": "push"}


class TestAuthVerification:
    def test_none_auth_passes(self):
        from app.services.integration_service import verify_auth
        integ = MagicMock()
        integ.auth_method = "none"
        assert verify_auth(integ, _make_request())

    def test_token_auth_passes(self):
        from app.services.integration_service import verify_auth
        from app.services.crypto import encrypt
        integ = MagicMock()
        integ.auth_method = "token"
        integ.auth_header = "X-Token"
        integ.auth_secret = encrypt("my-secret-token")
        req = _make_request(headers={"X-Token": "my-secret-token"})
        assert verify_auth(integ, req)

    def test_token_auth_fails(self):
        from app.services.integration_service import verify_auth
        from app.services.crypto import encrypt
        integ = MagicMock()
        integ.auth_method = "token"
        integ.auth_header = "X-Token"
        integ.auth_secret = encrypt("real-token")
        req = _make_request(headers={"X-Token": "wrong-token"})
        assert not verify_auth(integ, req)
