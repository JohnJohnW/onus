"""Close out compliance deadlines when the work that satisfies them is done.

Deadlines were only ever created, never completed, so the dashboard showed them as
perpetually pending. Callers invoke complete_deadlines from the flow that satisfies a
deadline (enrolment, annual report lodged, risk-assessment review, etc.), or a user
closes one manually. The caller owns the transaction."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import ComplianceDeadline


def complete_deadlines(db: Session, firm_id, deadline_type: str, user_id=None) -> int:
    """Mark every still-pending deadline of a type as done. Returns how many closed."""
    rows = db.scalars(
        select(ComplianceDeadline).where(
            ComplianceDeadline.firm_id == firm_id,
            ComplianceDeadline.deadline_type == deadline_type,
            ComplianceDeadline.status == "pending",
        )
    ).all()
    now = datetime.now(timezone.utc)
    for deadline in rows:
        deadline.status = "done"
        deadline.completed_at = now
        deadline.completed_by_user_id = user_id
    return len(rows)
