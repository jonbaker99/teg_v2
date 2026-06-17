"""Tests for the minimal admin auth helper (webapp/admin_auth.py)."""

import os

import pytest

from webapp import admin_auth


class _FakeReq:
    def __init__(self, cookies):
        self.cookies = cookies


class _FakeResp:
    def __init__(self):
        self.cookies = {}
        self.deleted = []

    def set_cookie(self, name, value, **kwargs):
        self.cookies[name] = value

    def delete_cookie(self, name, **kwargs):
        self.deleted.append(name)


@pytest.fixture(autouse=True)
def _set_password(monkeypatch):
    monkeypatch.setenv("WEBAPP_ADMIN_PASSWORD", "secret123")


def test_check_password():
    assert admin_auth.check_password("secret123") is True
    assert admin_auth.check_password("wrong") is False
    assert admin_auth.check_password("") is False


def test_cookie_roundtrip_authorises():
    resp = _FakeResp()
    admin_auth.set_auth_cookie(resp)
    token = resp.cookies[admin_auth.COOKIE_NAME]
    assert admin_auth.is_authed(_FakeReq({admin_auth.COOKIE_NAME: token})) is True


def test_wrong_cookie_rejected():
    assert admin_auth.is_authed(_FakeReq({admin_auth.COOKIE_NAME: "nope"})) is False
    assert admin_auth.is_authed(_FakeReq({})) is False


def test_cookie_invalidated_when_password_changes(monkeypatch):
    resp = _FakeResp()
    admin_auth.set_auth_cookie(resp)
    token = resp.cookies[admin_auth.COOKIE_NAME]
    # Rotating the password must invalidate the old cookie.
    monkeypatch.setenv("WEBAPP_ADMIN_PASSWORD", "different")
    assert admin_auth.is_authed(_FakeReq({admin_auth.COOKIE_NAME: token})) is False


def test_clear_cookie():
    resp = _FakeResp()
    admin_auth.clear_auth_cookie(resp)
    assert admin_auth.COOKIE_NAME in resp.deleted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
