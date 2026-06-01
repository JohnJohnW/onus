"""Governance endpoints — appoint compliance officer / senior manager."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import Firm, GovernanceRole, User
from schemas import GovernanceRolesRequest

router = APIRouter()


@router.post("/roles")
def set_roles(
    body: GovernanceRolesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    firm_id = current_user.firm_id
    now = datetime.now(timezone.utc)

    assignments = {
        "compliance_officer": body.compliance_officer_user_id or current_user.id,
        "senior_manager": body.senior_manager_user_id or current_user.id,
    }
    for role, user_id in assignments.items():
        gr = db.scalar(
            select(GovernanceRole).where(
                GovernanceRole.firm_id == firm_id, GovernanceRole.role == role
            )
        )
        if gr is None:
            gr = GovernanceRole(firm_id=firm_id, role=role)
            db.add(gr)
        gr.user_id = user_id
        gr.appointed_at = now
        gr.appointed_by_user_id = current_user.id
        gr.is_active = True

    firm = db.get(Firm, firm_id)
    firm.onboarding_step = body.onboarding_step if body.onboarding_step is not None else 2

    db.commit()
    return {"status": "ok", "onboarding_step": firm.onboarding_step}
