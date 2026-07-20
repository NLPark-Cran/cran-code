"""Tests for the v2 auth sliding-window rate limiter."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from cran_code.web.api_v2 import auth as auth_api


@pytest.fixture(autouse=True)
def _reset_buckets():
    auth_api._rate_limit_buckets.clear()
    yield
    auth_api._rate_limit_buckets.clear()


def _request(ip: str | None = "1.2.3.4", forwarded_for: str | None = None):
    headers: dict[str, str] = {}
    if forwarded_for is not None:
        headers["x-forwarded-for"] = forwarded_for
    client = SimpleNamespace(host=ip) if ip is not None else None
    return SimpleNamespace(headers=headers, client=client)


def test_allows_up_to_max_attempts():
    req = _request()
    for _ in range(auth_api._RATE_LIMIT_ATTEMPTS):
        auth_api._check_rate_limit(req)


def test_raises_429_when_limit_exceeded():
    req = _request()
    for _ in range(auth_api._RATE_LIMIT_ATTEMPTS):
        auth_api._check_rate_limit(req)
    with pytest.raises(HTTPException) as exc_info:
        auth_api._check_rate_limit(req)
    assert exc_info.value.status_code == 429
    assert "Too many attempts" in str(exc_info.value.detail)


def test_buckets_are_per_client_ip():
    for _ in range(auth_api._RATE_LIMIT_ATTEMPTS):
        auth_api._check_rate_limit(_request(ip="1.1.1.1"))
    # A different IP is not affected.
    auth_api._check_rate_limit(_request(ip="2.2.2.2"))
    with pytest.raises(HTTPException):
        auth_api._check_rate_limit(_request(ip="1.1.1.1"))


def test_x_forwarded_for_first_hop_wins():
    req = _request(ip="10.0.0.1", forwarded_for="9.9.9.9, 10.0.0.1")
    assert auth_api._client_ip(req) == "9.9.9.9"
    for _ in range(auth_api._RATE_LIMIT_ATTEMPTS):
        auth_api._check_rate_limit(req)
    # The proxy IP itself has a separate bucket.
    auth_api._check_rate_limit(_request(ip="10.0.0.1"))
    with pytest.raises(HTTPException):
        auth_api._check_rate_limit(req)


def test_missing_client_ip_falls_back_to_unknown():
    assert auth_api._client_ip(_request(ip=None)) == "unknown"


def test_window_expires_old_attempts(monkeypatch: pytest.MonkeyPatch):
    now = 1000.0
    monkeypatch.setattr(auth_api.time, "monotonic", lambda: now)
    req = _request()
    for _ in range(auth_api._RATE_LIMIT_ATTEMPTS):
        auth_api._check_rate_limit(req)
    with pytest.raises(HTTPException):
        auth_api._check_rate_limit(req)
    # After the window passes, attempts are allowed again.
    monkeypatch.setattr(
        auth_api.time, "monotonic", lambda: now + auth_api._RATE_LIMIT_WINDOW_SECONDS + 1
    )
    auth_api._check_rate_limit(req)
