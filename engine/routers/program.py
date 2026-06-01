"""AML/CTF program — the program container, policy set, and document-&-approve flow."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.drafting import draft_policy
from auth.dependencies import get_current_user
from database import get_db
from models import (
    AmlProgram,
    AuditLog,
    Firm,
    FirmRiskState,
    GovernanceApproval,
    GovernanceRole,
    Policy,
    RiskAssessment,
    User,
)
from schemas import (
    GovernanceRoleOut,
    PolicyOut,
    PolicyUpdate,
    ProgramApproveRequest,
    ProgramOut,
)

router = APIRouter()

# The seed policy catalogue — one policy per AML/CTF obligation area (Act s26F; Rules Pt 5).
POLICY_CATALOGUE: list[dict] = [
    {"area_key": "cdd", "title": "Customer due diligence", "obligation_key": "cdd", "act_reference": "Act s26F(3)(b); Rules s5-2"},
    {"area_key": "sof_sow", "title": "Source of funds / source of wealth triggers", "obligation_key": "sof_sow", "act_reference": "Rules s5-2(2)-(3)"},
    {"area_key": "enhanced_cdd", "title": "Enhanced customer due diligence", "obligation_key": "enhanced_cdd", "act_reference": "Act s32"},
    {"area_key": "pep", "title": "Politically exposed persons", "obligation_key": "pep", "act_reference": "Act s28(2)(e); Rules s5-5"},
    {"area_key": "sanctions", "title": "Targeted financial sanctions", "obligation_key": "sanctions", "act_reference": "Rules s5-3"},
    {"area_key": "transaction_monitoring", "title": "Transaction monitoring", "obligation_key": "transaction_monitoring", "act_reference": "Act s30; Rules s6-35"},
    {"area_key": "smr", "title": "Suspicious matter reporting & tipping-off", "obligation_key": "smr", "act_reference": "Act ss41, 123; Rules s5-12, s5-13"},
    {"area_key": "ttr", "title": "Threshold transaction reporting", "obligation_key": "ttr", "act_reference": "Act s43"},
    {"area_key": "annual_report", "title": "Annual compliance report", "obligation_key": "annual_report", "act_reference": "Act s47; Rules s9-9"},
    {"area_key": "record_keeping", "title": "Record keeping", "obligation_key": "record_keeping", "act_reference": "Act ss107-116"},
    {"area_key": "third_party_reliance", "title": "Reliance on third parties for CDD", "obligation_key": "third_party_reliance", "act_reference": "Act ss37A-38; Rules s5-5"},
    {"area_key": "employee_dd_training", "title": "Employee due diligence & AML/CTF training", "obligation_key": "employee_dd_training", "act_reference": "Act s26F(4)(d)-(e); Rules s5-8, s5-9"},
    {"area_key": "independent_evaluation", "title": "Independent evaluation", "obligation_key": "independent_evaluation", "act_reference": "Act s26F(4)(f); Rules s5-10"},
    {"area_key": "program_review", "title": "Program review & update", "obligation_key": "program_review", "act_reference": "Act ss26D, 26F(3)(c)-(d); Rules s5-15"},
    {"area_key": "governance", "title": "Governance & oversight", "obligation_key": "governance", "act_reference": "Act ss26H, 26J; Rules s5-6, s5-7"},
    {"area_key": "pf_controls", "title": "Proliferation financing controls", "obligation_key": "pf_controls", "act_reference": "Act s26C(1); Rules s5-3"},
]


def _latest_risk_assessment(db: Session, firm_id) -> Optional[RiskAssessment]:
    return db.scalar(
        select(RiskAssessment)
        .where(RiskAssessment.firm_id == firm_id)
        .order_by(RiskAssessment.version.desc(), RiskAssessment.created_at.desc())
    )


def _get_or_create_program(db: Session, firm_id) -> AmlProgram:
    program = db.scalar(select(AmlProgram).where(AmlProgram.firm_id == firm_id))
    if program is None:
        ra = _latest_risk_assessment(db, firm_id)
        program = AmlProgram(
            firm_id=firm_id,
            status="draft",
            risk_assessment_id=ra.id if ra else None,
        )
        db.add(program)
        db.flush()
        # Seed a draft policy per catalogue area.
        for entry in POLICY_CATALOGUE:
            db.add(
                Policy(
                    firm_id=firm_id,
                    program_id=program.id,
                    area_key=entry["area_key"],
                    obligation_key=entry["obligation_key"],
                    act_reference=entry["act_reference"],
                    title=entry["title"],
                    status="draft",
                )
            )
        db.commit()
        db.refresh(program)
    return program


def _policy_out(p: Policy) -> PolicyOut:
    return PolicyOut(
        id=p.id,
        area_key=p.area_key,
        title=p.title,
        body=p.body,
        status=p.status,
        obligation_key=p.obligation_key,
        act_reference=p.act_reference,
        documented=bool(p.body and p.body.strip()),
    )


def _serialize(db: Session, program: AmlProgram, firm_id) -> ProgramOut:
    policies = sorted(program.policies, key=lambda p: p.title)
    ra = db.get(RiskAssessment, program.risk_assessment_id) if program.risk_assessment_id else None
    roles = db.scalars(
        select(GovernanceRole).where(
            GovernanceRole.firm_id == firm_id, GovernanceRole.is_active.is_(True)
        )
    ).all()
    return ProgramOut(
        id=program.id,
        status=program.status,
        version=program.version,
        documented_at=program.documented_at,
        approved_by_name=program.approved_by_name,
        approved_by_role=program.approved_by_role,
        approved_at=program.approved_at,
        next_review_due=program.next_review_due_at,
        risk_assessment_status=ra.status if ra else None,
        documented_count=sum(1 for p in policies if p.body and p.body.strip()),
        total_count=len(policies),
        policies=[_policy_out(p) for p in policies],
        roles=[GovernanceRoleOut.model_validate(r) for r in roles],
    )


@router.get("", response_model=ProgramOut)
def get_program(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramOut:
    program = _get_or_create_program(db, current_user.firm_id)
    return _serialize(db, program, current_user.firm_id)


@router.patch("/policies/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: str,
    body: PolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PolicyOut:
    policy = db.get(Policy, policy_id)
    if policy is None or policy.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")
    if body.title is not None:
        policy.title = body.title
    if body.body is not None:
        policy.body = body.body
    if body.status in ("draft", "approved"):
        policy.status = body.status
    db.commit()
    db.refresh(policy)
    return _policy_out(policy)


@router.post("/policies/{policy_id}/draft", response_model=PolicyOut)
async def draft_policy_body(
    policy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PolicyOut:
    """Ask Onus to draft the policy body (a draft for human review — Onus never approves)."""
    policy = db.get(Policy, policy_id)
    if policy is None or policy.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")
    firm = db.get(Firm, current_user.firm_id)
    risk = db.scalar(select(FirmRiskState).where(FirmRiskState.firm_id == current_user.firm_id))
    draft = await draft_policy(
        title=policy.title,
        act_reference=policy.act_reference,
        firm_name=firm.name if firm else None,
        risk_rating=risk.overall_risk_rating if risk else None,
    )
    policy.body = draft
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="policy.ai_drafted",
            entity_type="policy",
            entity_id=policy.id,
        )
    )
    db.commit()
    db.refresh(policy)
    return _policy_out(policy)


@router.post("/submit-for-approval", response_model=ProgramOut)
def submit_for_approval(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramOut:
    program = _get_or_create_program(db, current_user.firm_id)
    existing = db.scalar(
        select(GovernanceApproval).where(
            GovernanceApproval.firm_id == current_user.firm_id,
            GovernanceApproval.subject_type == "program",
            GovernanceApproval.status == "pending",
        )
    )
    if existing is None:
        db.add(
            GovernanceApproval(
                firm_id=current_user.firm_id,
                title="Approve your AML/CTF program",
                rationale="A senior manager must approve the AML/CTF program before designated services are provided.",
                action_label="Review and approve",
                status="pending",
                subject_type="program",
                subject_id=program.id,
                due_at=datetime.now(timezone.utc) + timedelta(days=14),
            )
        )
    program.status = "under_review"
    db.commit()
    db.refresh(program)
    return _serialize(db, program, current_user.firm_id)


@router.post("/approve", response_model=ProgramOut)
def approve_program(
    body: ProgramApproveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramOut:
    """Senior-manager approval of the program (Act s26P) — records name, role, date."""
    program = _get_or_create_program(db, current_user.firm_id)
    now = datetime.now(timezone.utc)
    actor = current_user.full_name or current_user.email

    program.status = "approved"
    program.documented_at = program.documented_at or now
    program.approved_by_user_id = current_user.id
    program.approved_by_name = actor
    program.approved_by_role = "senior_manager"
    program.approved_at = now
    program.next_review_due_at = now + timedelta(days=365 * 3)  # at least every 3 years (s26F(3)(d))
    for p in program.policies:
        p.status = "approved"

    pending = db.scalar(
        select(GovernanceApproval).where(
            GovernanceApproval.firm_id == current_user.firm_id,
            GovernanceApproval.subject_type == "program",
            GovernanceApproval.status == "pending",
        )
    )
    if pending is not None:
        pending.status = "approved"
        pending.decision = "approved"
        pending.decision_reason = body.decision_reason
        pending.approved_by_user_id = current_user.id
        pending.approver_name = actor
        pending.approver_role = "senior_manager"
        pending.decided_at = now

    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="program.approved",
            entity_type="aml_program",
            entity_id=program.id,
            after_state={"status": "approved", "approver": actor},
        )
    )
    db.commit()
    db.refresh(program)
    return _serialize(db, program, current_user.firm_id)
