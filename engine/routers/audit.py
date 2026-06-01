"""Audit trail — read the firm's audit log."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import AuditLog, User
from schemas import AuditLogOut

router = APIRouter()


@router.get("", response_model=List[AuditLogOut])
def list_audit_log(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[AuditLogOut]:
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.firm_id == current_user.firm_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    ).all()

    # Resolve actor emails in one pass.
    user_ids = {r.user_id for r in rows if r.user_id is not None}
    emails: dict = {}
    if user_ids:
        for u in db.scalars(select(User).where(User.id.in_(user_ids))).all():
            emails[u.id] = u.email

    return [
        AuditLogOut(
            id=r.id,
            action=r.action,
            entity_type=r.entity_type,
            actor=emails.get(r.user_id),
            created_at=r.created_at,
        )
        for r in rows
    ]
