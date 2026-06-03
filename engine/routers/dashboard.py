"""Dashboard endpoints - the principal's daily agent feed."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.drafting import draft_compliance_brief
from auth.dependencies import get_current_user
from database import get_db
from models import (
    AgentTask,
    ComplianceDeadline,
    Firm,
    FirmRiskState,
    GovernanceApproval,
    User,
)
from schemas import (
    AgentActivityOut,
    BriefOut,
    DashboardSummary,
    PendingActionOut,
    UpcomingDeadlineOut,
)

router = APIRouter()

ACTION_WINDOW_DAYS = 14

DEADLINE_LABELS = {
    "enrolment": "Enrol your firm with AUSTRAC",
    "annual_report": "Lodge your annual compliance report",
    "risk_assessment_review": "Review your firm's risk assessment",
    "independent_evaluation": "Independent evaluation of your AML/CTF program",
}


def _deadline_label(deadline_type: str) -> str:
    return DEADLINE_LABELS.get(deadline_type, deadline_type.replace("_", " ").capitalize())


DEADLINE_HREFS = {
    "enrolment": "/settings",
    "annual_report": "/reporting",
    "risk_assessment_review": "/risk-profile",
    "independent_evaluation": "/evaluation",
}


def _deadline_href(deadline_type: str) -> str:
    return DEADLINE_HREFS.get(deadline_type, "/dashboard")


def _task_summary(task: AgentTask) -> str:
    out = task.output_state or {}
    if isinstance(out, dict) and out.get("summary"):
        return str(out["summary"])
    base = (task.task_type or task.agent_type or "Task").replace("_", " ").strip()
    return base[:1].upper() + base[1:] if base else "Task"


def _days_remaining(due_at: Optional[datetime], now: datetime) -> Optional[int]:
    if due_at is None:
        return None
    d = due_at if due_at.tzinfo is not None else due_at.replace(tzinfo=timezone.utc)
    return (d.astimezone(timezone.utc).date() - now.date()).days


def _estimate_label(minutes: Optional[int]) -> Optional[str]:
    if not minutes:
        return None
    if minutes < 60:
        return f"About {minutes} minutes"
    hours = minutes / 60
    if hours.is_integer():
        h = int(hours)
        return f"About {h} hour" + ("s" if h != 1 else "")
    return f"About {round(hours, 1)} hours"


@router.get("/summary", response_model=DashboardSummary)
def summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    firm_id = current_user.firm_id
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=ACTION_WINDOW_DAYS)

    risk = db.scalar(select(FirmRiskState).where(FirmRiskState.firm_id == firm_id))
    rating = risk.overall_risk_rating if risk else "unassessed"

    # --- Section 1: Action required ---
    approvals = db.scalars(
        select(GovernanceApproval)
        .where(
            GovernanceApproval.firm_id == firm_id,
            GovernanceApproval.status == "pending",
            GovernanceApproval.due_at.is_not(None),
            GovernanceApproval.due_at <= cutoff,
        )
        .order_by(GovernanceApproval.due_at.asc())
    ).all()
    action_deadlines = db.scalars(
        select(ComplianceDeadline)
        .where(
            ComplianceDeadline.firm_id == firm_id,
            ComplianceDeadline.status == "pending",
            ComplianceDeadline.due_at <= cutoff,
        )
        .order_by(ComplianceDeadline.due_at.asc())
    ).all()

    pending_actions: list[PendingActionOut] = []
    for a in approvals:
        pending_actions.append(
            PendingActionOut(
                id=a.id,
                kind="approval",
                title=a.title,
                why=a.rationale,
                estimate_label=_estimate_label(a.estimate_minutes),
                action_label=a.action_label,
                href="/compliance-program" if a.subject_type == "program" else "/risk-profile",
                due_at=a.due_at,
                days_remaining=_days_remaining(a.due_at, now),
            )
        )
    for d in action_deadlines:
        pending_actions.append(
            PendingActionOut(
                id=d.id,
                kind="deadline",
                title=_deadline_label(d.deadline_type),
                why="A compliance deadline is approaching.",
                estimate_label=None,
                action_label="View deadline",
                href=_deadline_href(d.deadline_type),
                due_at=d.due_at,
                days_remaining=_days_remaining(d.due_at, now),
            )
        )
    pending_actions.sort(key=lambda p: p.days_remaining if p.days_remaining is not None else 9999)

    # --- Section 2: Onus activity ---
    recent = db.scalars(
        select(AgentTask)
        .where(AgentTask.firm_id == firm_id)
        .order_by(AgentTask.created_at.desc())
        .limit(10)
    ).all()
    recent_activity = [
        AgentActivityOut(
            id=t.id,
            summary=_task_summary(t),
            created_at=t.created_at,
            human_action_required=t.human_action_required,
            human_action_outcome=t.human_action_type,
        )
        for t in recent
    ]

    # --- Section 3: Upcoming deadlines ---
    upcoming_rows = db.scalars(
        select(ComplianceDeadline)
        .where(
            ComplianceDeadline.firm_id == firm_id,
            ComplianceDeadline.status == "pending",
        )
        .order_by(ComplianceDeadline.due_at.asc())
        .limit(5)
    ).all()
    upcoming_deadlines = [
        UpcomingDeadlineOut(
            id=d.id,
            name=_deadline_label(d.deadline_type),
            due_at=d.due_at,
            days_remaining=_days_remaining(d.due_at, now),
        )
        for d in upcoming_rows
    ]

    return DashboardSummary(
        firm_risk_rating=rating,
        pending_actions=pending_actions,
        recent_agent_activity=recent_activity,
        upcoming_deadlines=upcoming_deadlines,
    )


@router.post("/brief", response_model=BriefOut)
async def brief(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BriefOut:
    """Onus drafts a short plain-English brief: what it did, what needs you, what is coming
    up. A summary of recent activity is sent to the AI to write the brief."""
    firm_id = current_user.firm_id
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    cutoff = now + timedelta(days=ACTION_WINDOW_DAYS)
    firm = db.get(Firm, firm_id)

    did_rows = db.scalars(
        select(AgentTask)
        .where(AgentTask.firm_id == firm_id, AgentTask.created_at >= week_ago)
        .order_by(AgentTask.created_at.desc())
        .limit(15)
    ).all()
    did = [_task_summary(t) for t in did_rows]

    approvals = db.scalars(
        select(GovernanceApproval).where(
            GovernanceApproval.firm_id == firm_id,
            GovernanceApproval.status == "pending",
            GovernanceApproval.due_at.is_not(None),
            GovernanceApproval.due_at <= cutoff,
        )
    ).all()
    action_deadlines = db.scalars(
        select(ComplianceDeadline).where(
            ComplianceDeadline.firm_id == firm_id,
            ComplianceDeadline.status == "pending",
            ComplianceDeadline.due_at <= cutoff,
        )
    ).all()
    needs = [a.title for a in approvals] + [
        _deadline_label(d.deadline_type) for d in action_deadlines
    ]

    upcoming_rows = db.scalars(
        select(ComplianceDeadline)
        .where(ComplianceDeadline.firm_id == firm_id, ComplianceDeadline.status == "pending")
        .order_by(ComplianceDeadline.due_at.asc())
        .limit(5)
    ).all()
    deadlines = [
        f"{_deadline_label(d.deadline_type)} (due {d.due_at.date()})"
        for d in upcoming_rows
        if d.due_at
    ]

    text = await draft_compliance_brief(
        firm_name=firm.name if firm else None, did=did, needs=needs, deadlines=deadlines
    )
    return BriefOut(brief=text)


@router.post("/deadlines/{deadline_id}/complete")
def complete_deadline(
    deadline_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Mark a compliance deadline done (manual completion)."""
    d = db.get(ComplianceDeadline, deadline_id)
    if d is None or d.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deadline not found.")
    d.status = "done"
    d.completed_at = datetime.now(timezone.utc)
    d.completed_by_user_id = current_user.id
    db.commit()
    return {"status": "done"}
