"""Governance endpoints - appoint compliance officer / senior manager."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import AuditLog, Firm, GovernanceRole, User
from schemas import GovernanceAssignRequest, GovernanceRoleOut, GovernanceRolesRequest

router = APIRouter()

VALID_ROLES = ("governing_body", "senior_manager", "compliance_officer", "independent_evaluator")


@router.get("/roles", response_model=list[GovernanceRoleOut])
def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GovernanceRoleOut]:
    rows = db.scalars(
        select(GovernanceRole).where(
            GovernanceRole.firm_id == current_user.firm_id, GovernanceRole.is_active.is_(True)
        )
    ).all()
    return [GovernanceRoleOut.model_validate(r) for r in rows]


@router.post("/assign", response_model=GovernanceRoleOut)
def assign_role(
    body: GovernanceAssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GovernanceRoleOut:
    """Assign a governance role, enforcing compliance-officer eligibility (Act s26J)."""
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role.")
    if body.role == "compliance_officer" and not (
        body.management_level and body.is_australian_resident and body.fit_and_proper_considered
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The compliance officer must be at management level, an Australian resident, "
            "and have a completed fit-and-proper consideration (Act s26J).",
        )
    user = db.get(User, body.user_id)
    if user is None or user.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    gr = db.scalar(
        select(GovernanceRole).where(
            GovernanceRole.firm_id == current_user.firm_id, GovernanceRole.role == body.role
        )
    )
    if gr is None:
        gr = GovernanceRole(firm_id=current_user.firm_id, role=body.role)
        db.add(gr)
    gr.user_id = body.user_id
    gr.appointed_at = datetime.now(timezone.utc)
    gr.appointed_by_user_id = current_user.id
    gr.is_active = True
    gr.management_level = body.management_level
    gr.is_australian_resident = body.is_australian_resident
    gr.fit_and_proper_considered = body.fit_and_proper_considered
    gr.qualifies_reason = body.qualifies_reason
    db.flush()
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="governance.role_assigned",
            entity_type="governance_role",
            entity_id=gr.id,
            after_state={"role": body.role},
        )
    )
    db.commit()
    db.refresh(gr)
    return GovernanceRoleOut.model_validate(gr)


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
    # A supplied user_id must belong to the caller's firm (prevents a cross-tenant write).
    for user_id in assignments.values():
        if user_id == current_user.id:
            continue
        u = db.get(User, user_id)
        if u is None or u.firm_id != firm_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That user is not part of your firm.",
            )
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
