"""Onboarding completion - compute risk, set deadlines, finish onboarding."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_log import record_agent_task
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
from routers.risk_assessment import aggregate_overall, review_interval_days

router = APIRouter()

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

    # Overall rating across all four risk categories, using the AUSTRAC / Law Society
    # combined method (any High -> High; two or more Mediums -> Medium; else Low).
    ratings = (
        [s.inherent_risk_rating for s in assessment.services]
        + [c.inherent_risk_rating for c in assessment.customer_types]
        + [d.inherent_risk_rating for d in assessment.delivery_channels]
        + [c.inherent_risk_rating for c in assessment.countries]
    )
    overall = aggregate_overall(ratings)
    assessment.overall_risk_rating = overall
    assessment.summary = _SUMMARIES.get(overall, _SUMMARIES["low"])
    # Review cadence depends on the rating (High yearly, Medium 2-yearly, Low 3-yearly).
    interval_days = review_interval_days(overall)
    assessment.next_review_due_at = now + timedelta(days=interval_days)

    risk_state = db.scalar(select(FirmRiskState).where(FirmRiskState.firm_id == firm_id))
    if risk_state is None:
        risk_state = FirmRiskState(firm_id=firm_id, overall_risk_rating=overall)
        db.add(risk_state)
    else:
        risk_state.overall_risk_rating = overall

    # Idempotent: create the standing deadlines only the first time onboarding is
    # completed, so a repeated /complete call cannot duplicate them.
    firm = db.get(Firm, firm_id)
    if not firm.onboarding_completed:
        db.add_all(
            [
                ComplianceDeadline(
                    firm_id=firm_id,
                    deadline_type="risk_assessment_review",
                    entity_type="risk_assessment",
                    entity_id=assessment.id,
                    due_at=now + timedelta(days=interval_days),
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
        record_agent_task(
            db,
            firm_id,
            task_type="documents_prepared",
            summary="Prepared your risk assessment and compliance program documents to review and download",
            human_action_required=True,
            human_action_type="review_documents",
        )

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
