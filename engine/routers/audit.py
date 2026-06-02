"""Audit trail - read and export the firm's audit log."""
from __future__ import annotations

import csv
import io
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import AuditLog, User
from schemas import AuditLogOut

router = APIRouter()


def _actor_emails(db: Session, rows) -> dict:
    """Resolve user_id -> email for the given audit rows in one query."""
    user_ids = {r.user_id for r in rows if r.user_id is not None}
    if not user_ids:
        return {}
    return {u.id: u.email for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()}


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
    emails = _actor_emails(db, rows)
    return [
        AuditLogOut(
            id=r.id,
            action=r.action,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            actor=emails.get(r.user_id),
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/export")
def export_audit_log(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download the firm's full audit log as CSV (for an AUSTRAC or Law Society request).

    Unlike the listing endpoint this is not capped at 100 rows - it is the complete,
    firm-scoped trail in reverse-chronological order.
    """
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.firm_id == current_user.firm_id)
        .order_by(AuditLog.created_at.desc())
    ).all()
    emails = _actor_emails(db, rows)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["timestamp_utc", "action", "entity_type", "entity_id", "actor"])
    for r in rows:
        writer.writerow(
            [
                r.created_at.isoformat() if r.created_at else "",
                r.action,
                r.entity_type or "",
                str(r.entity_id) if r.entity_id else "",
                emails.get(r.user_id) or "",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=onus-audit-log.csv"},
    )
