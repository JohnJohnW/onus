"""AML/CTF program - the program container, policy set, and document-&-approve flow."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_log import record_agent_task
from ai.drafting import draft_policy
from auth.dependencies import get_current_user, require_approver
from database import get_db
from docgen import build_program_docx
from pdfgen import build_program_pdf
from models import (
    AmlProgram,
    AuditLog,
    Firm,
    FirmRiskState,
    GovernanceApproval,
    GovernanceRole,
    Policy,
    ProgramChangeLog,
    ReviewTrigger,
    RiskAssessment,
    User,
)
from schemas import (
    GovernanceRoleOut,
    PolicyOut,
    PolicyUpdate,
    ProgramApproveRequest,
    ProgramChangeCreate,
    ProgramChangeOut,
    ProgramLifecycleOut,
    ProgramOut,
    ReviewTriggerCreate,
    ReviewTriggerOut,
)

router = APIRouter()

# The seed policy catalogue - one policy per AML/CTF obligation area (Act s26F; Rules Pt 5).
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


@router.get("/document")
def download_program_document(
    format: str = Query("docx", pattern="^(docx|pdf)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Generate a submission-ready AML/CTF compliance program document (Word .docx or PDF)."""
    program = _get_or_create_program(db, current_user.firm_id)
    firm = db.get(Firm, current_user.firm_id)
    firm_name = firm.name if firm else "Your firm"
    if format == "pdf":
        content = build_program_pdf(program, firm_name)
        media, ext = "application/pdf", "pdf"
    else:
        content = build_program_docx(program, firm_name)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="aml-ctf-program.{ext}"'},
    )


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
    if body.status is not None:
        if body.status not in ("draft", "approved"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid policy status."
            )
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
    """Ask Onus to draft the policy body (a draft for human review - Onus never approves)."""
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
    record_agent_task(
        db,
        current_user.firm_id,
        task_type="policy_drafted",
        summary=f'Drafted the "{policy.title}" policy for your review',
        human_action_required=True,
        human_action_type="review_policy",
        input_state={"policy_id": str(policy.id)},
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
    current_user: User = Depends(require_approver),
    db: Session = Depends(get_db),
) -> ProgramOut:
    """Senior-manager approval of the program (Act s26P) - records name, role, date."""
    program = _get_or_create_program(db, current_user.firm_id)
    now = datetime.now(timezone.utc)
    actor = current_user.full_name or current_user.email

    program.status = "approved"
    program.documented_at = program.documented_at or now
    program.approved_by_user_id = current_user.id
    program.approved_by_name = actor
    # Record the approver's actual role (admin or senior manager), not a fixed label,
    # so the s26P audit trail is accurate. require_approver permits both.
    program.approved_by_role = "admin" if current_user.role == "admin" else "senior_manager"
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


def _trigger_out(t: ReviewTrigger) -> ReviewTriggerOut:
    return ReviewTriggerOut(
        id=t.id,
        trigger_type=t.trigger_type,
        description=t.description,
        status=t.status,
        review_required_by=t.review_required_by,
        created_at=t.created_at,
    )


def _change_out(c: ProgramChangeLog) -> ProgramChangeOut:
    return ProgramChangeOut(
        id=c.id,
        entity_type=c.entity_type,
        change_summary=c.change_summary,
        trigger=c.trigger,
        is_material=c.is_material,
        documented=c.documented,
        due_at=c.due_at,
        changed_at=c.changed_at,
    )


@router.get("/lifecycle", response_model=ProgramLifecycleOut)
def get_lifecycle(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramLifecycleOut:
    program = _get_or_create_program(db, current_user.firm_id)
    triggers = db.scalars(
        select(ReviewTrigger)
        .where(ReviewTrigger.firm_id == current_user.firm_id, ReviewTrigger.status == "pending")
        .order_by(ReviewTrigger.triggered_at.desc())
    ).all()
    changes = db.scalars(
        select(ProgramChangeLog)
        .where(ProgramChangeLog.firm_id == current_user.firm_id)
        .order_by(ProgramChangeLog.changed_at.desc())
        .limit(20)
    ).all()
    return ProgramLifecycleOut(
        next_review_due=program.next_review_due_at,
        status=program.status,
        open_triggers=[_trigger_out(t) for t in triggers],
        changes=[_change_out(c) for c in changes],
    )


@router.post("/changes", response_model=ProgramChangeOut)
def log_change(
    body: ProgramChangeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgramChangeOut:
    """Log a program update; material changes need senior-manager approval (Step 4)."""
    program = _get_or_create_program(db, current_user.firm_id)
    now = datetime.now(timezone.utc)
    change = ProgramChangeLog(
        firm_id=current_user.firm_id,
        entity_type=body.entity_type,
        change_summary=body.change_summary,
        trigger=body.trigger,
        is_material=body.is_material,
        documented=True,  # logging it here documents it (Rules s5-15: within 14 days)
        due_at=now + timedelta(days=14),
        changed_by_user_id=current_user.id,
    )
    db.add(change)
    db.flush()
    if body.is_material:
        approval = GovernanceApproval(
            firm_id=current_user.firm_id,
            title="Approve program update",
            rationale=f"A material change to the {body.entity_type.replace('_', ' ')} needs senior-manager approval (Act s26P).",
            action_label="Review and approve",
            status="pending",
            subject_type="program",
            subject_id=program.id,
            due_at=now + timedelta(days=14),
        )
        db.add(approval)
        db.flush()
        change.approval_id = approval.id
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="program.change_logged",
            entity_type="aml_program",
            entity_id=program.id,
            after_state={"trigger": body.trigger, "material": body.is_material},
        )
    )
    db.commit()
    db.refresh(change)
    return _change_out(change)


@router.post("/triggers", response_model=ReviewTriggerOut)
def add_trigger(
    body: ReviewTriggerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewTriggerOut:
    """Register a significant-change / AUSTRAC-communication review trigger (Step 4)."""
    now = datetime.now(timezone.utc)
    trigger = ReviewTrigger(
        firm_id=current_user.firm_id,
        trigger_type=body.trigger_type,
        description=body.description,
        review_required_by=now,
    )
    db.add(trigger)
    db.flush()
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="program.review_triggered",
            entity_type="review_trigger",
            entity_id=trigger.id,
        )
    )
    db.commit()
    db.refresh(trigger)
    return _trigger_out(trigger)


@router.post("/triggers/{trigger_id}/resolve", response_model=ReviewTriggerOut)
def resolve_trigger(
    trigger_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReviewTriggerOut:
    """Close a review trigger once the program/policies have been reviewed in response."""
    trigger = db.get(ReviewTrigger, trigger_id)
    if trigger is None or trigger.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found.")
    trigger.status = "completed"
    trigger.completed_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="program.review_trigger_resolved",
            entity_type="review_trigger",
            entity_id=trigger.id,
        )
    )
    db.commit()
    db.refresh(trigger)
    return _trigger_out(trigger)
