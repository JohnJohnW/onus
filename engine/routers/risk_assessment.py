"""Risk assessment — current state, onboarding inputs, and approval flow."""
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
    Firm,
    FirmRiskState,
    GovernanceApproval,
    RiskAssessment,
    RiskAssessmentCustomerType,
    RiskAssessmentDeliveryChannel,
    RiskAssessmentService,
    ReviewTrigger,
    User,
)
from schemas import (
    CustomerTypesRequest,
    DeliveryChannelsRequest,
    RiskAssessmentOut,
    RiskItemOut,
    ServicesRequest,
)

router = APIRouter()

# AUSTRAC-guided inherent risk ratings (rating, plain-English explanation).
SERVICE_RULES: dict[str, tuple[str, str]] = {
    "Property transactions": ("medium", "Conveyancing and property transfers are a common channel for laundering money."),
    "Trust establishment": ("high", "Setting up trusts can obscure who really controls assets."),
    "Company formation": ("high", "Forming companies can hide who is really behind them."),
    "Client funds management": ("high", "Holding or moving client money directly is among the highest-risk work."),
    "Business sales": ("medium", "Buying and selling businesses can move significant value."),
}
CUSTOMER_RULES: dict[str, tuple[str, str]] = {
    "Individual people": ("low", "Everyday individuals with verifiable identities are lower risk."),
    "Small business owners": ("medium", "Small businesses need extra checks on ownership and source of funds."),
    "Large companies": ("medium", "Larger corporate structures require verifying control and ownership."),
    "Trusts or family offices": ("high", "Trusts and family offices can obscure beneficial ownership."),
    "Overseas clients": ("high", "Clients based overseas are harder to verify and carry higher risk."),
    "Government": ("low", "Government bodies are transparent and lower risk."),
}
CHANNEL_RULES: dict[str, tuple[str, str]] = {
    "Face to face always/usually": ("low", "Meeting clients in person makes identity verification straightforward."),
    "Face to face sometimes/rarely": ("medium", "Limited in-person contact means more reliance on remote checks."),
    "Remote often": ("medium", "Frequent remote onboarding needs stronger identity checks."),
    "Remote sometimes": ("low", "Occasional remote onboarding is lower risk alongside in-person contact."),
    "Online platforms yes": ("medium", "Onboarding via online platforms requires robust electronic verification."),
    "Overseas transactions regularly": ("high", "Regular cross-border transactions significantly raise risk."),
    "Overseas transactions sometimes": ("medium", "Occasional overseas transactions carry moderate risk."),
}


def _serialize(a: RiskAssessment, senior_manager_name: str) -> RiskAssessmentOut:
    def items(rows, name_attr):
        return [
            RiskItemOut(
                id=r.id,
                name=getattr(r, name_attr),
                rating=r.inherent_risk_rating,
                explanation=r.explanation or "",
            )
            for r in rows
        ]

    return RiskAssessmentOut(
        id=a.id,
        status=a.status,
        overall_rating=a.overall_risk_rating,
        summary=a.summary,
        next_review_due=a.next_review_due_at,
        updated_at=a.updated_at,
        created_at=a.created_at,
        approved_by_name=a.approved_by_name,
        approved_at=a.approved_at,
        senior_manager_name=senior_manager_name,
        services=items(a.services, "designated_service_type"),
        client_types=items(a.customer_types, "customer_type"),
        channels=items(a.delivery_channels, "channel_type"),
        countries=items(a.countries, "country"),
    )


def _current(db: Session, firm_id) -> Optional[RiskAssessment]:
    return db.scalar(
        select(RiskAssessment)
        .where(RiskAssessment.firm_id == firm_id)
        .order_by(RiskAssessment.version.desc(), RiskAssessment.created_at.desc())
    )


def _get_or_create(db: Session, firm_id) -> RiskAssessment:
    assessment = _current(db, firm_id)
    if assessment is None:
        assessment = RiskAssessment(firm_id=firm_id, version=1, status="draft")
        db.add(assessment)
        db.flush()
    return assessment


def _set_step(db: Session, firm_id, step: Optional[int], default: int) -> None:
    firm = db.get(Firm, firm_id)
    if firm is not None:
        firm.onboarding_step = step if step is not None else default


@router.get("/current", response_model=RiskAssessmentOut)
def current(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    assessment = _current(db, current_user.firm_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No risk assessment found.")
    return _serialize(assessment, current_user.full_name or current_user.email)


@router.post("/services")
def set_services(
    body: ServicesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    firm_id = current_user.firm_id
    assessment = _get_or_create(db, firm_id)
    for row in list(assessment.services):
        db.delete(row)
    db.flush()
    for name in body.services:
        rating, explanation = SERVICE_RULES.get(name, ("medium", f"{name} is assessed as medium inherent risk."))
        db.add(
            RiskAssessmentService(
                risk_assessment_id=assessment.id,
                firm_id=firm_id,
                designated_service_type=name,
                inherent_risk_rating=rating,
                explanation=explanation,
            )
        )
    _set_step(db, firm_id, body.onboarding_step, 3)
    db.commit()
    return {"status": "ok", "onboarding_step": 3, "count": len(body.services)}


@router.post("/customer-types")
def set_customer_types(
    body: CustomerTypesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    firm_id = current_user.firm_id
    assessment = _get_or_create(db, firm_id)
    for row in list(assessment.customer_types):
        db.delete(row)
    db.flush()
    for name in body.customer_types:
        rating, explanation = CUSTOMER_RULES.get(name, ("medium", f"{name} is assessed as medium inherent risk."))
        db.add(
            RiskAssessmentCustomerType(
                risk_assessment_id=assessment.id,
                firm_id=firm_id,
                customer_type=name,
                inherent_risk_rating=rating,
                explanation=explanation,
            )
        )
    _set_step(db, firm_id, body.onboarding_step, 4)
    db.commit()
    return {"status": "ok", "onboarding_step": 4, "count": len(body.customer_types)}


@router.post("/delivery-channels")
def set_delivery_channels(
    body: DeliveryChannelsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    firm_id = current_user.firm_id
    assessment = _get_or_create(db, firm_id)
    for row in list(assessment.delivery_channels):
        db.delete(row)
    db.flush()
    for name in body.channels:
        rating, explanation = CHANNEL_RULES.get(name, ("medium", f"{name} is assessed as medium inherent risk."))
        db.add(
            RiskAssessmentDeliveryChannel(
                risk_assessment_id=assessment.id,
                firm_id=firm_id,
                channel_type=name,
                inherent_risk_rating=rating,
                explanation=explanation,
            )
        )
    _set_step(db, firm_id, body.onboarding_step, 5)
    db.commit()
    return {"status": "ok", "onboarding_step": 5, "count": len(body.channels)}


@router.post("/approve", response_model=RiskAssessmentOut)
def approve(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    assessment = _current(db, current_user.firm_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No risk assessment to approve.")
    if assessment.status != "draft":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already approved.")

    now = datetime.now(timezone.utc)
    assessment.status = "approved"
    assessment.approved_by_name = current_user.full_name or current_user.email
    assessment.approved_by_user_id = current_user.id
    assessment.approved_at = now

    risk_state = db.scalar(select(FirmRiskState).where(FirmRiskState.firm_id == current_user.firm_id))
    if risk_state is not None:
        risk_state.overall_risk_rating = assessment.overall_risk_rating

    db.add(
        GovernanceApproval(
            firm_id=current_user.firm_id,
            title="Risk assessment approved",
            rationale=f"Risk assessment approved by {current_user.full_name or current_user.email}.",
            action_label="View",
            status="approved",
        )
    )
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="risk_assessment.approved",
            entity_type="risk_assessment",
            entity_id=assessment.id,
            after_state={"status": "approved"},
        )
    )
    db.commit()
    db.refresh(assessment)
    return _serialize(assessment, current_user.full_name or current_user.email)


@router.post("/request-changes")
def request_changes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    assessment = _current(db, current_user.firm_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No risk assessment.")
    actor = current_user.full_name or current_user.email
    db.add(
        ReviewTrigger(
            firm_id=current_user.firm_id,
            trigger_type="risk_assessment_changes_requested",
            description=f"Changes requested on the risk assessment by {actor}.",
            review_required_by=datetime.now(timezone.utc),
        )
    )
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="risk_assessment.changes_requested",
            entity_type="risk_assessment",
            entity_id=assessment.id,
        )
    )
    db.commit()
    return {"status": "ok"}
