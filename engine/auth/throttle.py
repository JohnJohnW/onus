"""In-memory per-account failed-login throttle.

A backstop against password brute-force / credential-stuffing on a specific account.
Keyed on the email address (not the client IP) on purpose: every request reaches the
engine through the web proxy, so all callers share the proxy's IP and IP-based limiting
would lump unrelated users together. Per-account limiting works correctly regardless.

This counter is per-process and in-memory. For a multi-instance deployment, also front
the API with an edge / WAF rate limiter (see the README production hardening checklist);
this is the application-level backstop, not the whole story.

Tunable via env:
  AUTH_MAX_FAILED_LOGINS            (default 10; <= 0 disables the throttle)
  AUTH_FAILED_LOGIN_WINDOW_SECONDS  (default 900 = 15 minutes)
"""
from __future__ import annotations

import os
import threading
import time

_MAX_FAILED = int(os.environ.get("AUTH_MAX_FAILED_LOGINS", "10"))
_WINDOW_SECONDS = int(os.environ.get("AUTH_FAILED_LOGIN_WINDOW_SECONDS", "900"))

_lock = threading.Lock()
_failures: dict[str, list[float]] = {}


def _key(email: str) -> str:
    return email.strip().lower()


def _recent(now: float, stamps: list[float]) -> list[float]:
    return [t for t in stamps if now - t < _WINDOW_SECONDS]


def is_locked(email: str) -> bool:
    """True if this account has had too many recent failed logins."""
    if _MAX_FAILED <= 0:
        return False
    now = time.time()
    with _lock:
        stamps = _recent(now, _failures.get(_key(email), []))
        _failures[_key(email)] = stamps
        return len(stamps) >= _MAX_FAILED


def record_failure(email: str) -> None:
    """Record one failed login attempt for this account."""
    if _MAX_FAILED <= 0:
        return
    now = time.time()
    with _lock:
        stamps = _recent(now, _failures.get(_key(email), []))
        stamps.append(now)
        _failures[_key(email)] = stamps


def clear(email: str) -> None:
    """Reset an account's failure count (call on a successful login)."""
    with _lock:
        _failures.pop(_key(email), None)
