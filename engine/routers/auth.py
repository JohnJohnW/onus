"""Authentication endpoints: signup, login, current user, refresh, and the SSO bridge."""
from __future__ import annotations

import os
import secrets as _secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import throttle
from auth.dependencies import get_current_user
from auth.jwt import create_access_token
from database import get_db, set_session_firm
from models import Firm, FirmRiskState, GovernanceRole, User
from schemas import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    OAuthBridgeRequest,
    SignupRequest,
    UserOut,
    UserWithFirm,
)
from security import hash_password, verify_password

router = APIRouter()


def _token_for(user: User) -> str:
    return create_access_token(
        user_id=str(user.id),
        firm_id=str(user.firm_id),
        role=user.role,
        email=user.email,
    )


@router.post("/signup", response_model=AuthResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    if db.scalar(select(User).where(User.email == body.email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists.",
        )

    firm = Firm(name=body.firm_name)
    db.add(firm)
    db.flush()  # populate firm.id

    # The firm now exists; pin RLS context so the firm-scoped inserts below pass.
    set_session_firm(db, firm.id)

    user = User(
        firm_id=firm.id,
        full_name=body.full_name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role="admin",
    )
    db.add(user)
    db.flush()  # populate user.id

    db.add(GovernanceRole(firm_id=firm.id, user_id=user.id, role="compliance_officer"))
    db.add(FirmRiskState(firm_id=firm.id))

    db.commit()
    db.refresh(user)

    return AuthResponse(access_token=_token_for(user), user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    # Per-account brute-force backstop: too many recent failures locks the account out
    # for a cooldown window, regardless of source IP (see auth/throttle.py).
    if throttle.is_locked(body.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait and try again.",
        )
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.hashed_password):
        throttle.record_failure(body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )
    throttle.clear(body.email)
    return AuthResponse(access_token=_token_for(user), user=UserOut.model_validate(user))


def _default_firm_name(full_name, email: str) -> str:
    base = (full_name or "").strip() or email.split("@")[0]
    return f"{base}'s firm"


@router.post("/oauth", response_model=AuthResponse)
def oauth_bridge(
    body: OAuthBridgeRequest,
    x_internal_secret: str = Header(default=""),
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Exchange a verified OAuth identity (from the trusted web tier) for an access token.

    The web tier authenticates the user with the OAuth provider (e.g. Google), then calls
    this with the verified email. It is gated by a shared secret (OAUTH_BRIDGE_SECRET) so
    only the web tier can mint tokens this way - it is NOT a public endpoint, and SSO is
    disabled unless the secret is set. Finds the user by email, or creates a firm + admin
    user for a new SSO identity (who then completes onboarding to set the real firm)."""
    bridge_secret = os.environ.get("OAUTH_BRIDGE_SECRET", "")
    if not bridge_secret or not _secrets.compare_digest(x_internal_secret, bridge_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")

    email = body.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is not None:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="This account has been deactivated."
            )
        return AuthResponse(access_token=_token_for(user), user=UserOut.model_validate(user))

    # New SSO identity: create a firm + admin user with no usable password (SSO only).
    firm = Firm(name=_default_firm_name(body.full_name, email))
    db.add(firm)
    db.flush()
    set_session_firm(db, firm.id)
    user = User(
        firm_id=firm.id,
        full_name=(body.full_name or email),
        email=email,
        hashed_password=hash_password(_secrets.token_urlsafe(32)),
        role="admin",
    )
    db.add(user)
    db.flush()
    db.add(GovernanceRole(firm_id=firm.id, user_id=user.id, role="compliance_officer"))
    db.add(FirmRiskState(firm_id=firm.id))
    db.commit()
    db.refresh(user)
    return AuthResponse(access_token=_token_for(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserWithFirm)
def me(current_user: User = Depends(get_current_user)) -> UserWithFirm:
    # Validated while the request's DB session is open so the firm relationship loads.
    return UserWithFirm.model_validate(current_user)


@router.post("/refresh", response_model=AuthResponse)
def refresh(current_user: User = Depends(get_current_user)) -> AuthResponse:
    """Issue a fresh access token for the already-authenticated caller.

    The web tier calls this in the background while the current token is still
    valid (once it is past the halfway point of its life), so an active session is
    never logged out mid-use. A fully expired, deactivated, or otherwise invalid
    token is rejected by ``get_current_user``; the web tier then routes the user to
    re-login. This deliberately requires a valid token - it is a rolling renewal,
    not a way to revive a dead session.
    """
    return AuthResponse(
        access_token=_token_for(current_user),
        user=UserOut.model_validate(current_user),
    )


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Change your own password (e.g. after an admin creates your account)."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your current password is incorrect.",
        )
    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    db.commit()
    return {"status": "ok"}
