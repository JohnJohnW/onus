"""Authentication endpoints: signup, login, and current user."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.jwt import create_access_token
from database import get_db
from models import Firm, FirmRiskState, GovernanceRole, User
from schemas import AuthResponse, LoginRequest, SignupRequest, UserOut, UserWithFirm
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
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    return AuthResponse(access_token=_token_for(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserWithFirm)
def me(current_user: User = Depends(get_current_user)) -> UserWithFirm:
    # Validated while the request's DB session is open so the firm relationship loads.
    return UserWithFirm.model_validate(current_user)
