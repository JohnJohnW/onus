"""Onboarding completion — compute risk, set deadlines, finish onboarding."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import (
    AuditLog,
    ComplianceDeadline,
    Firm,
    FirmRiskState,
    RiskAssessment,
    User,
)

router = APIRouter()

_RANK = {"low": 0, "medium": 1, "high": 2}
_RANK_REV = {0: "low", 1: "medium", 2: "high"}

_SUMMARIES = {
    "low": (
        "Your firm's overall money-laundering and terrorism-financing risk is low. The services "
        "you offer and the clients you act for sit at the lower-risk end, so Onus will keep "
        "standard checks in place and watch for anything that changes the picture."
    ),
    "medium": (
        "Your firm's overall money-laundering and terrorism-financing risk is medium. Some of your "
        "work and client types carry higher risk, so Onus applies enhanced checks on those matters "
        "while keeping your overall exposure manageable."
    ),
    "high": (
        "Your firm's overall money-laundering and terrorism-financing risk is high. You take on "
        "higher-risk services or clients, so Onus applies enhanced due diligence and closer "
        "monitoring across those matters."
    ),
}


def _overall_rating(ratings: list[str]) -> str:
    if not ratings:
        return "low"
    return _RANK_REV[max(_RANK.get(r, 0) for r in ratings)]


def _next_march_31(now: datetime) -> datetime:
    candidate = datetime(now.year, 3, 31, tzinfo=timezone.utc)
    if candidate <= now:
        candidate = datetime(now.year + 1, 3, 31, tzinfo=timezone.utc)
    return candidate


@router.post("/complete")
def complete(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    firm_id = current_user.firm_id
    now = datetime.now(timezone.utc)

    assessment = db.scalar(
        select(RiskAssessment)
        .where(RiskAssessment.firm_id == firm_id)
        .order_by(RiskAssessment.version.desc())
    )
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete the risk-assessment steps before finishing onboarding.",
        )

    # Overall rating from services + customer types (per spec).
    ratings = [s.inherent_risk_rating for s in assessment.services] + [
        c.inherent_risk_rating for c in assessment.customer_types
    ]
    overall = _overall_rating(ratings)
    assessment.overall_risk_rating = overall
    assessment.summary = _SUMMARIES[overall]
    assessment.next_review_due_at = now + timedelta(days=3 * 365)

    risk_state = db.scalar(select(FirmRiskState).where(FirmRiskState.firm_id == firm_id))
    if risk_state is None:
        risk_state = FirmRiskState(firm_id=firm_id, overall_risk_rating=overall)
        db.add(risk_state)
    else:
        risk_state.overall_risk_rating = overall

    db.add_all(
        [
            ComplianceDeadline(
                firm_id=firm_id,
                deadline_type="risk_assessment_review",
                entity_type="risk_assessment",
                entity_id=assessment.id,
                due_at=now + timedelta(days=3 * 365),
            ),
            ComplianceDeadline(
                firm_id=firm_id,
                deadline_type="independent_evaluation",
                due_at=now + timedelta(days=3 * 365),
            ),
            ComplianceDeadline(
                firm_id=firm_id,
                deadline_type="annual_report",
                due_at=_next_march_31(now),
            ),
        ]
    )

    firm = db.get(Firm, firm_id)
    firm.onboarding_completed = True
    firm.onboarding_step = 7

    db.add(
        AuditLog(
            firm_id=firm_id,
            user_id=current_user.id,
            action="onboarding.completed",
            entity_type="firm",
            entity_id=firm_id,
            after_state={"onboarding_completed": True, "overall_risk_rating": overall},
        )
    )

    db.commit()
    return {
        "onboarding_completed": True,
        "onboarding_step": 7,
        "overall_risk_rating": overall,
    }
