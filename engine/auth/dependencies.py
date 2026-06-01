"""FastAPI auth dependencies: resolve the current user and set RLS firm context."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth.jwt import decode_access_token
from database import get_db
from models import User

bearer_scheme = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Validate the bearer token, load the user, and pin the firm for RLS.

    After the user is resolved, ``app.current_firm_id`` is set on the database
    session (transaction-local) so Postgres row-level-security policies can scope
    every query to the caller's firm via ``current_setting('app.current_firm_id')``.
    """
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise cred_exc

    user_id = payload.get("user_id")
    firm_id = payload.get("firm_id")
    if not user_id or not firm_id:
        raise cred_exc

    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        raise cred_exc

    user = db.get(User, uid)
    if user is None:
        raise cred_exc

    # Pin the firm context for row-level security. is_local=true scopes it to the
    # current transaction, so it never leaks across pooled connections.
    db.execute(
        text("SELECT set_config('app.current_firm_id', :firm_id, true)"),
        {"firm_id": str(firm_id)},
    )
    return user
