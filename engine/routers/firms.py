"""Firm endpoints - onboarding updates and settings."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, require_admin
from database import get_db
from deadlines import complete_deadlines
from models import ComplianceDeadline, Firm, GovernanceRole, User
from schemas import (
    FirmOut,
    FirmSettingsOut,
    FirmUpdate,
    GovernanceRoleOut,
    UserCreate,
    UserCreatedOut,
    UserOut,
    UserRoleUpdate,
)
from security import hash_password

router = APIRouter()

# AUSTRAC enrolment deadline for Tranche 2 entities.
ENROLMENT_DEADLINE = datetime(2026, 7, 29, tzinfo=timezone.utc)


@router.get("/{firm_id}", response_model=FirmSettingsOut)
def get_firm(
    firm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FirmSettingsOut:
    if firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your firm.")
    firm = db.get(Firm, firm_id)
    if firm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firm not found.")
    users = db.scalars(select(User).where(User.firm_id == firm_id)).all()
    roles = db.scalars(select(GovernanceRole).where(GovernanceRole.firm_id == firm_id)).all()
    return FirmSettingsOut(
        firm=FirmOut.model_validate(firm),
        users=[UserOut.model_validate(u) for u in users],
        governance_roles=[GovernanceRoleOut.model_validate(r) for r in roles],
    )


@router.patch("/{firm_id}", response_model=FirmOut)
def update_firm(
    firm_id: uuid.UUID,
    body: FirmUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FirmOut:
    if firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your firm.")
    firm = db.get(Firm, firm_id)
    if firm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firm not found.")

    data = body.model_dump(exclude_unset=True)
    for field in (
        "name",
        "abn",
        "firm_size",
        "practice_areas",
        "austrac_enrolment_number",
        "enrolment_status",
    ):
        if field in data:
            setattr(firm, field, data[field])
    if data.get("onboarding_step") is not None:
        firm.onboarding_step = data["onboarding_step"]

    # Step 6: if not yet enrolled, create the AUSTRAC enrolment deadline.
    if data.get("enrolment_status") in ("not_enrolled", "in_progress"):
        existing = db.scalar(
            select(ComplianceDeadline).where(
                ComplianceDeadline.firm_id == firm_id,
                ComplianceDeadline.deadline_type == "enrolment",
            )
        )
        if existing is None:
            db.add(
                ComplianceDeadline(
                    firm_id=firm_id, deadline_type="enrolment", due_at=ENROLMENT_DEADLINE
                )
            )
    elif data.get("enrolment_status") == "enrolled":
        # Enrolment is done; close the enrolment deadline.
        complete_deadlines(db, firm_id, "enrolment", current_user.id)

    db.commit()
    db.refresh(firm)
    return firm


@router.post("/users", response_model=UserCreatedOut)
def add_user(
    body: UserCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserCreatedOut:
    """Add a colleague to the firm. Returns a one-time temporary password for the
    admin to share; the colleague changes it after first login (no email yet)."""
    if body.role not in ("admin", "member"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role must be admin or member.")
    if db.scalar(select(User).where(User.email == body.email)) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An account with this email already exists.")
    temporary_password = secrets.token_urlsafe(12)
    user = User(
        firm_id=admin.firm_id,
        full_name=body.full_name,
        email=body.email,
        hashed_password=hash_password(temporary_password),
        role=body.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserCreatedOut(user=UserOut.model_validate(user), temporary_password=temporary_password)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    body: UserRoleUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    """Change a colleague's role or activate/deactivate them (admin only)."""
    user = db.get(User, user_id)
    if user is None or user.firm_id != admin.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.id == admin.id and (body.is_active is False or body.role == "member"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot demote or deactivate your own account.",
        )
    if body.role is not None:
        if body.role not in ("admin", "member"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role must be admin or member.")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.flush()
    # The firm must always keep at least one active admin.
    remaining_admin = db.scalar(
        select(User).where(
            User.firm_id == admin.firm_id, User.role == "admin", User.is_active.is_(True)
        )
    )
    if remaining_admin is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The firm must keep at least one active admin.",
        )
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
