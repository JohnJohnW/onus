"""Independent evaluation of the AML/CTF program (AUSTRAC Step 5; Transitional Rules s17)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import (
    AuditLog,
    EvaluationFinding,
    EvaluationReport,
    Evaluator,
    Firm,
    IndependentEvaluation,
    ReviewTrigger,
    User,
)
from schemas import (
    EvaluationOut,
    EvaluationReportRequest,
    EvaluationScheduleRequest,
    EvaluationsOut,
    EvaluatorOut,
    EvaluatorRequest,
    FindingOut,
    FindingUpdate,
)

router = APIRouter()


def _first_eval_deadline(aan: Optional[str]) -> tuple[date, bool]:
    """Staggered first-evaluation deadline by the last 2 digits of the AUSTRAC enrolment id (s17)."""
    digits = "".join(c for c in (aan or "") if c.isdigit())
    if len(digits) >= 2:
        second_last_odd = int(digits[-2]) % 2 == 1
        last_odd = int(digits[-1]) % 2 == 1
        if second_last_odd and last_odd:
            return date(2029, 6, 30), True
        if second_last_odd and not last_odd:
            return date(2029, 12, 31), True
        if not second_last_odd and not last_odd:
            return date(2030, 6, 30), True
        return date(2030, 12, 31), True
    return date(2029, 6, 30), False  # earliest bucket until the enrolment id is known


def _evaluator_out(ev: Optional[Evaluator]) -> Optional[EvaluatorOut]:
    if ev is None:
        return None
    return EvaluatorOut(
        id=ev.id,
        name=ev.name,
        kind=ev.kind,
        independence_confirmed=ev.independence_confirmed,
        is_compliance_officer=ev.is_compliance_officer,
        selection_rationale=ev.selection_rationale,
    )


def _eval_out(e: IndependentEvaluation) -> EvaluationOut:
    return EvaluationOut(
        id=e.id,
        status=e.status,
        frequency_months=e.frequency_months,
        frequency_rationale=e.frequency_rationale,
        is_first_evaluation=e.is_first_evaluation,
        statutory_deadline=e.statutory_deadline.isoformat() if e.statutory_deadline else None,
        scheduled_for=e.scheduled_for.isoformat() if e.scheduled_for else None,
        report_received_at=e.report_received_at,
        distributed_to_governing_body_at=e.distributed_to_governing_body_at,
        distributed_to_senior_manager_at=e.distributed_to_senior_manager_at,
        evaluator=_evaluator_out(e.evaluator),
        has_report=e.report is not None,
        findings=[
            FindingOut(
                id=f.id,
                area=f.area,
                is_adverse=f.is_adverse,
                description=f.description,
                remediation_action=f.remediation_action,
                status=f.status,
                wont_fix_reason=f.wont_fix_reason,
            )
            for f in e.findings
        ],
    )


def _get_eval(db: Session, firm_id, eval_id) -> IndependentEvaluation:
    e = db.get(IndependentEvaluation, eval_id)
    if e is None or e.firm_id != firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found.")
    return e


@router.get("", response_model=EvaluationsOut)
def list_evaluations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationsOut:
    firm = db.get(Firm, current_user.firm_id)
    deadline, known = _first_eval_deadline(firm.austrac_enrolment_number if firm else None)
    rows = db.scalars(
        select(IndependentEvaluation)
        .where(IndependentEvaluation.firm_id == current_user.firm_id)
        .order_by(IndependentEvaluation.created_at.desc())
    ).all()
    return EvaluationsOut(
        first_evaluation_deadline=deadline.isoformat(),
        enrolment_known=known,
        evaluations=[_eval_out(e) for e in rows],
    )


@router.post("", response_model=EvaluationOut)
def schedule_evaluation(
    body: EvaluationScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationOut:
    firm = db.get(Firm, current_user.firm_id)
    statutory = None
    if body.is_first_evaluation:
        statutory, _ = _first_eval_deadline(firm.austrac_enrolment_number if firm else None)
    scheduled = None
    if body.scheduled_for:
        try:
            scheduled = date.fromisoformat(body.scheduled_for)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date.")
    e = IndependentEvaluation(
        firm_id=current_user.firm_id,
        status="scheduled",
        frequency_months=body.frequency_months,
        frequency_rationale=body.frequency_rationale,
        is_first_evaluation=body.is_first_evaluation,
        statutory_deadline=statutory,
        scheduled_for=scheduled,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _eval_out(e)


@router.post("/{eval_id}/evaluator", response_model=EvaluationOut)
def assign_evaluator(
    eval_id: str,
    body: EvaluatorRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationOut:
    e = _get_eval(db, current_user.firm_id, eval_id)
    # Independence gate (Step 5 p.6): the evaluator cannot be the compliance officer / team.
    if body.is_compliance_officer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The compliance officer (or compliance team) cannot be the independent evaluator (Step 5).",
        )
    if not body.independence_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirm the evaluator's independence before assigning them.",
        )
    if e.evaluator is not None:
        db.delete(e.evaluator)
        db.flush()
    db.add(
        Evaluator(
            firm_id=current_user.firm_id,
            evaluation_id=e.id,
            name=body.name,
            kind=body.kind,
            independence_confirmed=body.independence_confirmed,
            is_compliance_officer=body.is_compliance_officer,
            independence_checklist=body.independence_checklist,
            suitability_scorecard=body.suitability_scorecard,
            selection_rationale=body.selection_rationale,
        )
    )
    if e.status == "scheduled":
        e.status = "in_progress"
    db.commit()
    db.refresh(e)
    return _eval_out(e)


@router.post("/{eval_id}/report", response_model=EvaluationOut)
def submit_report(
    eval_id: str,
    body: EvaluationReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationOut:
    e = _get_eval(db, current_user.firm_id, eval_id)
    if e.report is not None:
        # The prior report and findings are replaced, not versioned. Record the
        # supersession in the immutable audit trail first so the change is traceable.
        db.add(
            AuditLog(
                firm_id=current_user.firm_id,
                user_id=current_user.id,
                action="evaluation.report_superseded",
                entity_type="independent_evaluation",
                entity_id=e.id,
                after_state={
                    "superseded_report_id": str(e.report.id),
                    "prior_findings": len(list(e.findings)),
                },
            )
        )
        db.delete(e.report)
    for f in list(e.findings):
        db.delete(f)
    db.flush()
    db.add(
        EvaluationReport(
            evaluation_id=e.id,
            summary_of_process=body.summary_of_process,
            aspects_reviewed=body.aspects_reviewed,
            method=body.method,
            findings_risk_assessment=body.findings_risk_assessment,
            findings_policy_design=body.findings_policy_design,
            findings_compliance=body.findings_compliance,
            items_tested=body.items_tested,
            files_sampled=body.files_sampled,
            sampling_method=body.sampling_method,
            document_ref=body.document_ref,
        )
    )
    now = datetime.now(timezone.utc)
    adverse = 0
    for f in body.findings:
        db.add(
            EvaluationFinding(
                firm_id=current_user.firm_id,
                evaluation_id=e.id,
                area=f.area,
                is_adverse=f.is_adverse,
                description=f.description,
                remediation_action=f.remediation_action,
            )
        )
        if f.is_adverse:
            adverse += 1
            db.add(
                ReviewTrigger(
                    firm_id=current_user.firm_id,
                    trigger_type="evaluation_adverse_finding",
                    description=f"Adverse evaluation finding ({f.area}): {f.description[:140]}",
                    review_required_by=now,
                )
            )
    e.report_received_at = now
    e.status = "remediating" if adverse else "report_received"
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="evaluation.report_received",
            entity_type="independent_evaluation",
            entity_id=e.id,
            after_state={"adverse_findings": adverse},
        )
    )
    db.commit()
    db.refresh(e)
    return _eval_out(e)


@router.post("/{eval_id}/distribute", response_model=EvaluationOut)
def distribute_report(
    eval_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EvaluationOut:
    """Record distribution to the governing body + approving senior manager (Step 5 p.10)."""
    e = _get_eval(db, current_user.firm_id, eval_id)
    if e.report is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No report to distribute.")
    now = datetime.now(timezone.utc)
    e.distributed_to_governing_body_at = now
    e.distributed_to_senior_manager_at = now
    db.commit()
    db.refresh(e)
    return _eval_out(e)


@router.patch("/findings/{finding_id}", response_model=FindingOut)
def update_finding(
    finding_id: str,
    body: FindingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FindingOut:
    f = db.get(EvaluationFinding, finding_id)
    if f is None or f.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found.")
    if body.status in ("open", "in_progress", "done", "wont_fix"):
        if body.status == "wont_fix" and not (body.wont_fix_reason or f.wont_fix_reason):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A reason is required when a finding won't be fixed (Step 5 p.13).",
            )
        f.status = body.status
    if body.remediation_action is not None:
        f.remediation_action = body.remediation_action
    if body.wont_fix_reason is not None:
        f.wont_fix_reason = body.wont_fix_reason
    db.commit()
    db.refresh(f)
    return FindingOut(
        id=f.id,
        area=f.area,
        is_adverse=f.is_adverse,
        description=f.description,
        remediation_action=f.remediation_action,
        status=f.status,
        wont_fix_reason=f.wont_fix_reason,
    )
