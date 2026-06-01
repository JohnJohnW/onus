"""Firm endpoints — onboarding firm-detail and enrolment updates."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import ComplianceDeadline, Firm, User
from schemas import FirmOut, FirmUpdate

router = APIRouter()

# AUSTRAC enrolment deadline for Tranche 2 entities.
ENROLMENT_DEADLINE = datetime(2026, 7, 29, tzinfo=timezone.utc)


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

    db.commit()
    db.refresh(firm)
    return firm
