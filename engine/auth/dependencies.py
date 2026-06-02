"""FastAPI auth dependencies: resolve the current user and set RLS firm context."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.jwt import decode_access_token
from database import get_db, set_session_firm
from models import GovernanceRole, User

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
    if user is None or not user.is_active:
        raise cred_exc

    # Pin the firm for row-level security on this session (current transaction now,
    # and every later one via the after_begin listener in database.py).
    set_session_firm(db, firm_id)
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Gate firm-administration actions (managing users and governance roles)."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an admin.",
        )
    return current_user


def require_approver(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Gate program/risk-assessment approval to an admin or the firm's designated,
    active senior manager (the person the Act puts the approval on, s26P)."""
    if current_user.role == "admin":
        return current_user
    is_senior_manager = db.scalar(
        select(GovernanceRole).where(
            GovernanceRole.firm_id == current_user.firm_id,
            GovernanceRole.role == "senior_manager",
            GovernanceRole.user_id == current_user.id,
            GovernanceRole.is_active.is_(True),
        )
    )
    if is_senior_manager is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin or the designated senior manager may approve.",
        )
    return current_user
