"""Risk assessment endpoints — the firm's live risk state and approval flow."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import (
    AuditLog,
    FirmRiskState,
    GovernanceApproval,
    RiskAssessment,
    User,
)
from schemas import RiskAssessmentOut, RiskItemOut

router = APIRouter()


def _serialize(a: RiskAssessment, senior_manager_name: str) -> RiskAssessmentOut:
    return RiskAssessmentOut(
        id=a.id,
        status=a.status,
        overall_rating=a.overall_rating,
        summary=a.summary,
        next_review_due=a.next_review_due,
        updated_at=a.updated_at,
        created_at=a.created_at,
        approved_by_name=a.approved_by_name,
        approved_at=a.approved_at,
        senior_manager_name=senior_manager_name,
        services=[
            RiskItemOut(id=s.id, name=s.service_name, rating=s.rating, explanation=s.explanation)
            for s in a.services
        ],
        client_types=[
            RiskItemOut(id=c.id, name=c.client_type, rating=c.rating, explanation=c.explanation)
            for c in a.client_types
        ],
        channels=[
            RiskItemOut(id=c.id, name=c.channel, rating=c.rating, explanation=c.explanation)
            for c in a.channels
        ],
        countries=[
            RiskItemOut(id=c.id, name=c.country, rating=c.rating, explanation=c.explanation)
            for c in a.countries
        ],
    )


def _current(db: Session, firm_id) -> Optional[RiskAssessment]:
    return db.scalar(
        select(RiskAssessment)
        .where(RiskAssessment.firm_id == firm_id)
        .order_by(RiskAssessment.created_at.desc())
    )


@router.get("/current", response_model=RiskAssessmentOut)
def current(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    assessment = _current(db, current_user.firm_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk assessment found for this firm.",
        )
    return _serialize(assessment, current_user.full_name)


@router.post("/approve", response_model=RiskAssessmentOut)
def approve(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    assessment = _current(db, current_user.firm_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk assessment to approve.",
        )
    if assessment.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This risk assessment has already been approved.",
        )

    now = datetime.now(timezone.utc)
    assessment.status = "approved"
    assessment.approved_by_name = current_user.full_name
    assessment.approved_at = now

    # Reflect the approved rating on the firm's live risk state (drives the dashboard).
    risk_state = db.scalar(
        select(FirmRiskState).where(FirmRiskState.firm_id == current_user.firm_id)
    )
    if risk_state is not None:
        risk_state.risk_level = assessment.overall_rating

    # Record the governance approval and an audit-trail entry.
    db.add(
        GovernanceApproval(
            firm_id=current_user.firm_id,
            title="Risk assessment approved",
            rationale=f"Risk assessment approved by {current_user.full_name}.",
            action_label="View",
            status="approved",
        )
    )
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="risk_assessment.approved",
            detail=f"Risk assessment {assessment.id} approved by {current_user.full_name}.",
        )
    )

    db.commit()
    db.refresh(assessment)
    return _serialize(assessment, current_user.full_name)
