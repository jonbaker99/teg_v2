"""Minimal admin auth for the webapp.

This is deliberately lightweight — it is **not** real security. Its only job is
to stop a random crawler/bot from accidentally hitting the data-update endpoint
(which writes to the GitHub repo and triggers a paid LLM commentary run). One
shared password, set via the ``WEBAPP_ADMIN_PASSWORD`` env var, kept in a cookie
so you log in once on your phone.
"""

import hashlib
import hmac
import os

COOKIE_NAME = "teg_admin"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _password() -> str:
    """The configured admin password (falls back to a default if unset)."""
    return os.getenv("WEBAPP_ADMIN_PASSWORD", "teg")


def _expected_token() -> str:
    """Opaque cookie token derived from the password (so it isn't stored raw)."""
    return hashlib.sha256(_password().encode("utf-8")).hexdigest()


def check_password(candidate: str) -> bool:
    """Constant-time-ish comparison of a submitted password."""
    return hmac.compare_digest(candidate or "", _password())


def is_authed(request) -> bool:
    """True if the request carries a valid admin cookie."""
    token = request.cookies.get(COOKIE_NAME, "")
    return hmac.compare_digest(token, _expected_token())


def set_auth_cookie(response) -> None:
    """Mark the response as logged-in."""
    response.set_cookie(
        COOKIE_NAME,
        _expected_token(),
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


def clear_auth_cookie(response) -> None:
    """Log out."""
    response.delete_cookie(COOKIE_NAME)
