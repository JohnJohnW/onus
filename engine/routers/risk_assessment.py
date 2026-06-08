"""Risk assessment - current state, onboarding inputs, and approval flow."""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_log import record_agent_task
from ai.drafting import draft_risk_assessment_summary, generate_review
from ai.managed import (
    cleanup_review_run,
    managed_agents_enabled,
    poll_review_run,
    start_review_run,
)
from auth.dependencies import get_current_user, require_approver
from database import get_db
from deadlines import complete_deadlines
from docgen import build_risk_assessment_docx
from pdfgen import build_risk_assessment_pdf
from models import (
    AgentTask,
    AuditLog,
    AustracCommunication,
    ComplianceDeadline,
    Firm,
    FirmRiskState,
    GovernanceApproval,
    RiskAssessment,
    RiskAssessmentCountry,
    RiskAssessmentCustomerType,
    RiskAssessmentDeliveryChannel,
    RiskAssessmentService,
    ReviewTrigger,
    User,
)
from schemas import (
    AgentReviewStartOut,
    AgentReviewStatusOut,
    CommunicationIn,
    CommunicationOut,
    CountriesRequest,
    CountryItemOut,
    CustomerTypesRequest,
    DeliveryChannelsRequest,
    MethodologyRequest,
    PfRequest,
    ReviewOut,
    RiskAssessmentOut,
    RiskItemOut,
    ServicesRequest,
)

router = APIRouter()

# AUSTRAC-guided inherent risk ratings (rating, plain-English explanation).
SERVICE_RULES: dict[str, tuple[str, str]] = {
    "Property transactions": ("high", "AUSTRAC's national risk assessment rates real estate and conveyancing a high money-laundering vulnerability."),
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


# ----- Scoring engine -----
#
# Operative method: each selected service / customer type / delivery channel / country
# carries an inherent rating (impact-based, from AUSTRAC's published vulnerability
# ratings), and the overall rating is aggregated by the AUSTRAC / Law Society combined
# method below. The likelihood x impact matrix for the medium-complexity tier is
# specified in docs/specs/risk-methodology.md and activates once per-factor
# likelihood/impact capture is added; it is not applied yet, so we do not ship it here.

_REVIEW_INTERVAL_DAYS = {"high": 365, "medium": 730, "low": 1095}


def aggregate_overall(ratings: list[str]) -> str:
    """Overall ML/TF rating per the AUSTRAC / Law Society combined method: High if any
    factor is High; otherwise Medium if two or more factors are Medium; otherwise Low
    (when at least one factor is rated). 'unassessed' when nothing has been rated yet."""
    if any(r == "high" for r in ratings):
        return "high"
    if sum(1 for r in ratings if r == "medium") >= 2:
        return "medium"
    if ratings:
        return "low"
    return "unassessed"


def review_interval_days(rating: Optional[str]) -> int:
    """Risk-assessment review cadence by overall rating (AUSTRAC / Law Society small-
    practice guide): High yearly, Medium every 2 years, Low every 3 years."""
    return _REVIEW_INTERVAL_DAYS.get(rating or "", 1095)


def _basel_band(score) -> Optional[str]:
    if score is None:
        return None
    s = float(score)
    if s <= 5:
        return "low"
    if s <= 6:
        return "medium"
    return "high"


def _country_rating(row: RiskAssessmentCountry) -> str:
    """Force High on any AUSTRAC high-risk trigger, else Basel band (default low)."""
    if (
        row.fatf_listed
        or row.sanctions_listed
        or row.prescribed_foreign_country
        or row.tax_haven
        or row.terrorism_support
    ):
        return "high"
    return _basel_band(row.basel_score) or "low"


def _country_explanation(row: RiskAssessmentCountry) -> str:
    # AUSTRAC's method auto-rates a country High on two triggers: a FATF high-risk
    # listing or a DFAT/UN sanctions listing. The other three are Onus's own enhanced
    # factors (good practice, not mandated by AUSTRAC), so we label them as such.
    mandated, enhanced = [], []
    if row.fatf_listed:
        mandated.append("on the FATF list of high-risk jurisdictions")
    if row.sanctions_listed:
        mandated.append(
            "subject to Australian/UN sanctions - you must not deal with a sanctioned "
            "person, so screen any connected party before acting"
        )
    if row.prescribed_foreign_country:
        enhanced.append("a prescribed foreign country")
    if row.tax_haven:
        enhanced.append("a known tax haven")
    if row.terrorism_support:
        enhanced.append("linked to terrorism financing")
    if mandated or enhanced:
        parts = []
        if mandated:
            parts.append("AUSTRAC automatic high-risk: " + "; ".join(mandated))
        if enhanced:
            parts.append("Onus enhanced factor: " + "; ".join(enhanced))
        return f"{row.country} is rated high risk. " + ". ".join(parts) + "."
    if row.basel_score is not None:
        return f"{row.country} scored {row.basel_score} on the Basel AML Index ({_basel_band(row.basel_score)} risk)."
    return f"{row.country} has no elevated country-risk indicators recorded."


def _recompute_overall(db: Session, assessment_id) -> str:
    """Overall rating aggregated across all four risk categories (see aggregate_overall).
    Planned (not-yet-offered) factors are excluded so the rating reflects current risk."""
    ratings: list[str] = []
    for model in (
        RiskAssessmentService,
        RiskAssessmentCustomerType,
        RiskAssessmentDeliveryChannel,
        RiskAssessmentCountry,
    ):
        stmt = select(model.inherent_risk_rating).where(model.risk_assessment_id == assessment_id)
        if hasattr(model, "is_planned"):
            stmt = stmt.where(model.is_planned.isnot(True))
        for (rating,) in db.execute(stmt).all():
            if rating:
                ratings.append(rating)
    return aggregate_overall(ratings)


def _serialize(a: RiskAssessment, senior_manager_name: str) -> RiskAssessmentOut:
    def items(rows, name_attr):
        return [
            RiskItemOut(
                id=r.id,
                name=getattr(r, name_attr),
                rating=r.inherent_risk_rating,
                explanation=r.explanation or "",
                likelihood=r.likelihood,
                impact=r.impact,
                data_source=r.data_source,
                is_planned=r.is_planned,
            )
            for r in rows
        ]

    def country_items(rows):
        return [
            CountryItemOut(
                id=r.id,
                name=r.country,
                rating=r.inherent_risk_rating,
                explanation=r.explanation or "",
                basel_score=float(r.basel_score) if r.basel_score is not None else None,
                fatf_listed=r.fatf_listed,
                sanctions_listed=r.sanctions_listed,
                prescribed_foreign_country=r.prescribed_foreign_country,
                tax_haven=r.tax_haven,
                terrorism_support=r.terrorism_support,
            )
            for r in rows
        ]

    return RiskAssessmentOut(
        id=a.id,
        status=a.status,
        overall_rating=a.overall_risk_rating,
        summary=a.summary,
        methodology=a.methodology,
        complexity_tier=a.complexity_tier,
        pf_assessed=a.pf_assessed,
        pf_risk_rating=a.pf_risk_rating,
        pf_rationale=a.pf_rationale,
        next_review_due=a.next_review_due_at,
        updated_at=a.updated_at,
        created_at=a.created_at,
        approved_by_name=a.approved_by_name,
        approved_at=a.approved_at,
        senior_manager_name=senior_manager_name,
        services=items(a.services, "designated_service_type"),
        client_types=items(a.customer_types, "customer_type"),
        channels=items(a.delivery_channels, "channel_type"),
        countries=country_items(a.countries),
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
    db.flush()
    assessment.overall_risk_rating = _recompute_overall(db, assessment.id)
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
    db.flush()
    assessment.overall_risk_rating = _recompute_overall(db, assessment.id)
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
    db.flush()
    assessment.overall_risk_rating = _recompute_overall(db, assessment.id)
    db.commit()
    return {"status": "ok", "onboarding_step": 5, "count": len(body.channels)}


@router.post("/approve", response_model=RiskAssessmentOut)
def approve(
    current_user: User = Depends(require_approver),
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

    # Approving the assessment satisfies any pending risk-assessment review deadline.
    complete_deadlines(db, current_user.firm_id, "risk_assessment_review", current_user.id)

    # Schedule the next review at a cadence set by the approved rating (AUSTRAC / Law
    # Society small-practice guide: High yearly, Medium 2-yearly, Low 3-yearly).
    interval = review_interval_days(assessment.overall_risk_rating)
    assessment.next_review_due_at = now + timedelta(days=interval)
    db.add(
        ComplianceDeadline(
            firm_id=current_user.firm_id,
            deadline_type="risk_assessment_review",
            entity_type="risk_assessment",
            entity_id=assessment.id,
            due_at=now + timedelta(days=interval),
        )
    )

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


@router.post("/draft-summary", response_model=RiskAssessmentOut)
async def draft_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    """Ask Onus to draft the overall risk-assessment summary for review. A draft only -
    Onus never approves the assessment; that stays with the senior manager."""
    assessment = _current(db, current_user.firm_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No risk assessment found.")
    if assessment.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This assessment is already approved. Request changes before re-drafting.",
        )
    firm = db.get(Firm, current_user.firm_id)
    draft = await draft_risk_assessment_summary(
        firm_name=firm.name if firm else None,
        overall_rating=assessment.overall_risk_rating,
        services=[(s.designated_service_type, s.inherent_risk_rating) for s in assessment.services],
        customer_types=[(c.customer_type, c.inherent_risk_rating) for c in assessment.customer_types],
        channels=[(d.channel_type, d.inherent_risk_rating) for d in assessment.delivery_channels],
        countries=[(c.country, c.inherent_risk_rating) for c in assessment.countries],
        pf_rating=assessment.pf_risk_rating,
    )
    assessment.summary = draft
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="risk_assessment.ai_drafted",
            entity_type="risk_assessment",
            entity_id=assessment.id,
        )
    )
    record_agent_task(
        db,
        current_user.firm_id,
        task_type="risk_summary_drafted",
        summary="Drafted your risk-assessment summary for review",
        human_action_required=True,
        human_action_type="review_risk_assessment",
        input_state={"risk_assessment_id": str(assessment.id)},
    )
    db.commit()
    fresh = _current(db, current_user.firm_id)
    return _serialize(fresh, current_user.full_name or current_user.email)


@router.post("/review", response_model=ReviewOut)
async def run_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewOut:
    """Onus runs a periodic review and returns it as structured data (rating, drivers,
    recommended actions, checks, recommendation) for the app to render interactively. A
    draft for the senior manager - approving the assessment still discharges the review."""
    assessment = _current(db, current_user.firm_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No risk assessment found.")
    firm = db.get(Firm, current_user.firm_id)
    last_approved = assessment.approved_at.date().isoformat() if assessment.approved_at else None
    try:
        review = await generate_review(
            firm_name=firm.name if firm else None,
            overall_rating=assessment.overall_risk_rating,
            last_approved_on=last_approved,
            services=[(s.designated_service_type, s.inherent_risk_rating) for s in assessment.services],
            customer_types=[(c.customer_type, c.inherent_risk_rating) for c in assessment.customer_types],
            channels=[(d.channel_type, d.inherent_risk_rating) for d in assessment.delivery_channels],
            countries=[(c.country, c.inherent_risk_rating) for c in assessment.countries],
            pf_rating=assessment.pf_risk_rating,
        )
        result = ReviewOut(**review)
    except Exception as exc:  # AI failure or malformed shape -> graceful error, not a 500
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not run a review right now. Please try again.",
        ) from exc
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="risk_assessment.reviewed",
            entity_type="risk_assessment",
            entity_id=assessment.id,
        )
    )
    record_agent_task(
        db,
        current_user.firm_id,
        task_type="risk_review",
        summary="Completed a periodic review of your risk assessment",
        human_action_required=True,
        human_action_type="review_risk_assessment",
        input_state={"risk_assessment_id": str(assessment.id)},
        output_state={"review": result.model_dump(mode="json")},
    )
    db.commit()
    return result


@router.get("/last-review", response_model=Optional[ReviewOut])
def last_review(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[ReviewOut]:
    """The most recently run review, persisted on its agent task, so it renders on page load
    (not only right after the user clicks Review with Onus)."""
    task = db.scalar(
        select(AgentTask)
        .where(AgentTask.firm_id == current_user.firm_id, AgentTask.task_type == "risk_review")
        .order_by(AgentTask.created_at.desc())
    )
    review = (task.output_state or {}).get("review") if task else None
    return ReviewOut(**review) if review else None


@router.post("/agent-review", response_model=AgentReviewStartOut)
async def agent_review_start(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentReviewStartOut:
    """Start an autonomous review on the Claude Managed Agents platform (cloud session).
    Beta + feature-flagged; the session runs in Anthropic's managed sandbox. Drafts only -
    the senior manager still approves."""
    if not managed_agents_enabled():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Managed Agents review is not enabled.")
    assessment = _current(db, current_user.firm_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No risk assessment found.")
    firm = db.get(Firm, current_user.firm_id)

    def fmt(rows, attr) -> str:
        return "; ".join(f"{getattr(r, attr)} ({r.inherent_risk_rating})" for r in rows) or "none"

    task = (
        f"Review the AML/CTF risk assessment for {firm.name if firm else 'the firm'} and write a "
        f"periodic-review note.\n"
        f"Overall rating: {assessment.overall_risk_rating}.\n"
        f"Designated services: {fmt(assessment.services, 'designated_service_type')}.\n"
        f"Customer types: {fmt(assessment.customer_types, 'customer_type')}.\n"
        f"Delivery channels: {fmt(assessment.delivery_channels, 'channel_type')}.\n"
        f"Countries: {fmt(assessment.countries, 'country')}.\n"
        f"Proliferation financing: {assessment.pf_risk_rating or 'not yet assessed'}.\n"
        f"Last approved: "
        f"{assessment.approved_at.date().isoformat() if assessment.approved_at else 'not yet approved'}."
    )
    model = os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-6"
    try:
        ids = await start_review_run(model=model, task=task)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not start the managed-agent review. Please try again.",
        )
    record_agent_task(
        db,
        current_user.firm_id,
        task_type="agent_review",
        summary="Started an autonomous risk review (Managed Agents)",
        human_action_required=True,
        human_action_type="review_risk_assessment",
        input_state=ids,
    )
    db.commit()
    return AgentReviewStartOut(session_id=ids["session_id"])


@router.get("/agent-review/{session_id}", response_model=AgentReviewStatusOut)
async def agent_review_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentReviewStatusOut:
    """Poll a managed-agent review (firm-scoped via the stored session). When the agent's
    turn is done, return its note and tear down the session/agent/environment."""
    if not managed_agents_enabled():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Managed Agents review is not enabled.")
    task = db.scalar(
        select(AgentTask).where(
            AgentTask.firm_id == current_user.firm_id,
            AgentTask.input_state["session_id"].astext == session_id,
        )
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review session not found.")
    ids = task.input_state or {}
    try:
        result = await poll_review_run(session_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not check the review right now. Please try again.",
        )
    if result["done"]:
        await cleanup_review_run(
            session_id=session_id,
            agent_id=ids.get("agent_id", ""),
            environment_id=ids.get("environment_id", ""),
        )
        return AgentReviewStatusOut(status="done", note=result["note"])
    return AgentReviewStatusOut(status="running", note=None)


@router.post("/methodology", response_model=RiskAssessmentOut)
def set_methodology(
    body: MethodologyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    if body.methodology not in ("impact_only", "likelihood_x_impact"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid methodology.")
    assessment = _get_or_create(db, current_user.firm_id)
    assessment.methodology = body.methodology
    if body.complexity_tier is not None:
        if body.complexity_tier not in ("low", "medium", "high"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid complexity tier."
            )
        assessment.complexity_tier = body.complexity_tier
    db.commit()
    fresh = _current(db, current_user.firm_id)
    return _serialize(fresh, current_user.full_name or current_user.email)


@router.put("/countries", response_model=RiskAssessmentOut)
def set_countries(
    body: CountriesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    """Set the country list with override flags; rating is computed (AUSTRAC Step 2 country guidance; FATF / DFAT lists)."""
    firm_id = current_user.firm_id
    assessment = _get_or_create(db, firm_id)
    # Validate and de-duplicate (last value wins per country) before mutating.
    seen: dict = {}
    for c in body.countries:
        if c.basel_score is not None and not 0.0 <= c.basel_score <= 10.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Basel score must be between 0 and 10.",
            )
        seen[c.country.strip().lower()] = c
    for row in list(assessment.countries):
        db.delete(row)
    db.flush()
    for c in seen.values():
        row = RiskAssessmentCountry(
            risk_assessment_id=assessment.id,
            firm_id=firm_id,
            country=c.country,
            basel_score=c.basel_score,
            fatf_listed=c.fatf_listed,
            sanctions_listed=c.sanctions_listed,
            prescribed_foreign_country=c.prescribed_foreign_country,
            tax_haven=c.tax_haven,
            terrorism_support=c.terrorism_support,
            inherent_risk_rating="low",
            explanation="",
        )
        row.inherent_risk_rating = _country_rating(row)
        row.explanation = _country_explanation(row)
        db.add(row)
    if body.onboarding_step is not None:
        _set_step(db, firm_id, body.onboarding_step, body.onboarding_step)
    db.flush()
    assessment.overall_risk_rating = _recompute_overall(db, assessment.id)
    db.commit()
    fresh = _current(db, firm_id)
    return _serialize(fresh, current_user.full_name or current_user.email)


@router.post("/pf", response_model=RiskAssessmentOut)
def set_proliferation_financing(
    body: PfRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessmentOut:
    """Four-criterion PF screen (AUSTRAC Step 2 PF guidance; Act s26C(1))."""
    assessment = _get_or_create(db, current_user.firm_id)
    low = all(
        [
            body.australia_only_operations,
            body.no_high_risk_jurisdiction_customers,
            body.no_value_or_dual_use_goods_movement,
            body.no_pf_relevant_service,
        ]
    )
    assessment.pf_assessed = True
    assessment.pf_risk_rating = "low" if low else "medium"
    assessment.pf_rationale = (
        "All four AUSTRAC 'lower PF risk' criteria are met - no separate proliferation-financing "
        "policies required, but PF must still be recorded as assessed."
        if low
        else "One or more PF risk criteria are not met - assess proliferation-financing controls "
        "and consider enhanced sanctions screening."
    )
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="risk_assessment.pf_assessed",
            entity_type="risk_assessment",
            entity_id=assessment.id,
            after_state={"pf_risk_rating": assessment.pf_risk_rating},
        )
    )
    db.commit()
    fresh = _current(db, current_user.firm_id)
    return _serialize(fresh, current_user.full_name or current_user.email)


def _comm_out(comm: AustracCommunication, reviewer: Optional[str]) -> CommunicationOut:
    return CommunicationOut(
        id=comm.id,
        source_label=comm.source_label,
        communicated_on=comm.communicated_on.isoformat() if comm.communicated_on else None,
        relevance_note=comm.relevance_note,
        change_made=comm.change_made,
        considered_on=comm.considered_on.isoformat() if comm.considered_on else None,
        reviewer=reviewer,
        created_at=comm.created_at,
    )


@router.get("/communications", response_model=list[CommunicationOut])
def list_communications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CommunicationOut]:
    rows = db.scalars(
        select(AustracCommunication)
        .where(AustracCommunication.firm_id == current_user.firm_id)
        .order_by(AustracCommunication.created_at.desc())
    ).all()
    reviewer_ids = {r.reviewer_user_id for r in rows if r.reviewer_user_id}
    emails = {}
    if reviewer_ids:
        for u in db.scalars(select(User).where(User.id.in_(reviewer_ids))).all():
            emails[u.id] = u.full_name or u.email
    return [_comm_out(r, emails.get(r.reviewer_user_id)) for r in rows]


@router.post("/communications", response_model=CommunicationOut)
def add_communication(
    body: CommunicationIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommunicationOut:
    """Log an AUSTRAC communication; raises a review trigger (Step 4)."""
    try:
        comm_date = date.fromisoformat(body.communicated_on) if body.communicated_on else None
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date.")
    now = datetime.now(timezone.utc)
    if comm_date is not None and comm_date > now.date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Communication date cannot be in the future.",
        )
    trigger = ReviewTrigger(
        firm_id=current_user.firm_id,
        trigger_type="austrac_communication",
        description=f"AUSTRAC communication logged: {body.source_label}.",
        review_required_by=now,
    )
    db.add(trigger)
    db.flush()
    comm = AustracCommunication(
        firm_id=current_user.firm_id,
        source_label=body.source_label,
        communicated_on=comm_date,
        relevance_note=body.relevance_note,
        change_made=body.change_made,
        considered_on=now.date(),
        reviewer_user_id=current_user.id,
        review_trigger_id=trigger.id,
    )
    db.add(comm)
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="risk_assessment.austrac_communication_logged",
            entity_type="risk_assessment",
            entity_id=comm.id,
        )
    )
    db.commit()
    db.refresh(comm)
    return _comm_out(comm, current_user.full_name or current_user.email)


@router.get("/export")
def export_assessment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Export the current risk assessment as a Markdown document."""
    a = _current(db, current_user.firm_id)
    if a is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No risk assessment found.")
    firm = db.get(Firm, current_user.firm_id)
    L: list[str] = [f"# AML/CTF Risk Assessment - {firm.name if firm else 'the firm'}", ""]
    L.append(f"- **Status:** {a.status}  -  **Overall rating:** {a.overall_risk_rating}")
    L.append(f"- **Methodology:** {a.methodology} ({a.complexity_tier} complexity)")
    if a.next_review_due_at:
        L.append(f"- **Next review due:** {a.next_review_due_at.date()}")
    if a.approved_by_name:
        approved = a.approved_at.date() if a.approved_at else ""
        L.append(f"- **Approved by:** {a.approved_by_name} ({approved})")
    L.append("")
    if a.summary:
        L += [a.summary, ""]

    def section(title: str, rows, name_attr: str) -> None:
        L.append(f"## {title}")
        if not rows:
            L.append("_None recorded._")
        for r in rows:
            extra = []
            if getattr(r, "likelihood", None) and getattr(r, "impact", None):
                extra.append(f"{r.likelihood} x {r.impact}")
            if getattr(r, "data_source", None):
                extra.append(f"source: {r.data_source}")
            meta = f" ({'; '.join(extra)})" if extra else ""
            L.append(f"- **{getattr(r, name_attr)}** - {r.inherent_risk_rating}{meta}")
            if r.explanation:
                L.append(f"  - {r.explanation}")
        L.append("")

    section("Designated services", a.services, "designated_service_type")
    section("Customer types", a.customer_types, "customer_type")
    section("Delivery channels", a.delivery_channels, "channel_type")

    L.append("## Countries")
    if not a.countries:
        L.append("_None recorded._")
    for c in a.countries:
        flags = [
            name
            for name, on in [
                ("FATF", c.fatf_listed),
                ("sanctions", c.sanctions_listed),
                ("prescribed", c.prescribed_foreign_country),
                ("tax haven", c.tax_haven),
                ("terrorism", c.terrorism_support),
            ]
            if on
        ]
        fl = f" [{', '.join(flags)}]" if flags else ""
        L.append(f"- **{c.country}** - {c.inherent_risk_rating}{fl}")
    L.append("")

    L.append("## Proliferation financing")
    L.append(f"{'Assessed' if a.pf_assessed else 'Not assessed'} - {a.pf_risk_rating or 'n/a'}")
    if a.pf_rationale:
        L.append(a.pf_rationale)
    L += ["", "---", "_Generated by Onus. Not legal advice._"]
    return {"filename": "risk-assessment.md", "content": "\n".join(L)}


@router.get("/document")
def download_document(
    format: str = Query("docx", pattern="^(docx|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Generate a submission-ready risk assessment document (Word .docx or PDF)."""
    a = _current(db, current_user.firm_id)
    if a is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No risk assessment found.")
    firm = db.get(Firm, current_user.firm_id)
    firm_name = firm.name if firm else "Your firm"
    if format == "pdf":
        content = build_risk_assessment_pdf(a, firm_name)
        media, ext = "application/pdf", "pdf"
    else:
        content = build_risk_assessment_docx(a, firm_name)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="risk-assessment.{ext}"'},
    )
