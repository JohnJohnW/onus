"""JWT access-token creation and validation.

Tokens are signed with ``JWT_SECRET`` (HS256) and expire after 24 hours. The
payload carries ``user_id``, ``firm_id``, ``role`` and ``email``.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from jose import JWTError
from jose import jwt as jose_jwt

ALGORITHM = "HS256"
EXPIRY_HOURS = 24


def _secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is not set.")
    return secret


def create_access_token(*, user_id: str, firm_id: str, role: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "firm_id": firm_id,
        "role": role,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=EXPIRY_HOURS)).timestamp()),
    }
    return jose_jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a token, returning its payload.

    Raises:
        ValueError: if the token is invalid or expired.
    """
    try:
        return jose_jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
