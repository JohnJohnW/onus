"""Reporting & record keeping — SMR/TTR/IFTI/annual, deadlines, and retention (Act Pt 3, Pt 10)."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.drafting import draft_smr_narrative
from auth.dependencies import get_current_user
from database import get_db
from models import AuditLog, Client, Matter, Record, Report, ReportDecisionLog, User
from schemas import (
    DecisionRequest,
    RecordOut,
    ReportCreate,
    ReportOut,
    ReportUpdate,
)

router = APIRouter()
records_router = APIRouter()

REPORT_TYPES = {"smr", "ttr", "ifti", "annual_compliance", "cross_border_bni"}
TTR_THRESHOLD = 10000  # physical currency ≥ $10,000 (Act s5)
RETENTION_YEARS = 7  # Act ss107-116


def _add_business_days(start: datetime, n: int) -> datetime:
    d = start
    added = 0
    while added < n:
        d = d + timedelta(days=1)
        if d.weekday() < 5:  # Mon-Fri (public holidays not modelled — see spec)
            added += 1
    return d


def _compute_due(
    report_type: str, *, tf: bool, lpp: bool, trigger: datetime, period_end: Optional[str]
) -> tuple[Optional[datetime], Optional[str]]:
    if report_type == "smr":
        if tf:
            return trigger + timedelta(hours=24), "smr_tf_24h"
        if lpp:
            return _add_business_days(trigger, 5), "smr_lpp_5bd"
        return _add_business_days(trigger, 3), "smr_3bd"
    if report_type == "ttr":
        return _add_business_days(trigger, 10), "ttr_10bd"
    if report_type == "ifti":
        return _add_business_days(trigger, 10), "ifti_10bd"
    if report_type == "annual_compliance":
        if period_end:
            try:
                pe = date.fromisoformat(period_end)
                return datetime(pe.year, 9, 30, tzinfo=timezone.utc), "annual_3mo"
            except ValueError:
                return None, "annual_3mo"
        return None, "annual_3mo"
    return None, None


def _hash(payload: Optional[dict]) -> str:
    return hashlib.sha256(json.dumps(payload or {}, sort_keys=True).encode()).hexdigest()


def _report_out(r: Report) -> ReportOut:
    return ReportOut(
        id=r.id,
        type=r.type,
        status=r.status,
        related_client_id=r.related_client_id,
        related_matter_id=r.related_matter_id,
        deadline_basis=r.deadline_basis,
        lpp_claimed=r.lpp_claimed,
        lpp_form_ref=r.lpp_form_ref,
        due_at=r.due_at,
        lodged_at=r.lodged_at,
        reference_number=r.reference_number,
        created_at=r.created_at,
    )


@router.get("", response_model=list[ReportOut])
def list_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReportOut]:
    rows = db.scalars(
        select(Report).where(Report.firm_id == current_user.firm_id).order_by(Report.created_at.desc())
    ).all()
    return [_report_out(r) for r in rows]


@router.post("", response_model=ReportOut)
def create_report(
    body: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    if body.type not in REPORT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown report type.")
    payload = body.payload or {}
    if body.type == "ttr":
        amount = body.amount if body.amount is not None else payload.get("physical_currency_value_aud")
        if amount is not None and amount < TTR_THRESHOLD:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Below the ${TTR_THRESHOLD:,} threshold transaction reporting threshold.",
            )
    now = datetime.now(timezone.utc)
    due, basis = _compute_due(
        body.type, tf=body.tf, lpp=body.lpp_claimed, trigger=now, period_end=body.reporting_period_end
    )
    report = Report(
        firm_id=current_user.firm_id,
        type=body.type,
        status="draft",
        related_client_id=body.related_client_id,
        related_matter_id=body.related_matter_id,
        payload=payload,
        deadline_basis=basis,
        lpp_claimed=body.lpp_claimed,
        due_at=due,
        content_hash=_hash(payload),
    )
    db.add(report)
    db.flush()
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action=f"report.{body.type}.drafted",
            entity_type="report",
            entity_id=report.id,
        )
    )
    db.commit()
    db.refresh(report)
    return _report_out(report)


def _add_record(db: Session, firm_id, category: str, entity_id, basis: str = "from_creation") -> None:
    today = datetime.now(timezone.utc).date()
    retention_until = today + timedelta(days=365 * RETENTION_YEARS) if basis != "from_no_longer_relevant" else None
    db.add(
        Record(
            firm_id=firm_id,
            category=category,
            entity_type="report",
            entity_id=entity_id,
            retention_basis=basis,
            basis_date=today,
            retention_until=retention_until,
        )
    )


@router.patch("/{report_id}", response_model=ReportOut)
def update_report(
    report_id: str,
    body: ReportUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    r = db.get(Report, report_id)
    if r is None or r.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    if body.payload is not None:
        r.payload = body.payload
        r.content_hash = _hash(body.payload)
    if body.reference_number is not None:
        r.reference_number = body.reference_number
    if body.lpp_claimed is not None:
        r.lpp_claimed = body.lpp_claimed
    if body.lpp_form_ref is not None:
        r.lpp_form_ref = body.lpp_form_ref
    if body.status in ("draft", "ready", "lodged", "not_required"):
        r.status = body.status
        if body.status == "lodged":
            r.lodged_at = datetime.now(timezone.utc)
            r.lodged_by_user_id = current_user.id
            _add_record(db, current_user.firm_id, "report", r.id)
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action=f"report.{r.type}.{r.status}",
            entity_type="report",
            entity_id=r.id,
        )
    )
    db.commit()
    db.refresh(r)
    return _report_out(r)


@router.post("/{report_id}/decision", response_model=ReportOut)
def record_decision(
    report_id: str,
    body: DecisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    r = db.get(Report, report_id)
    if r is None or r.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    db.add(
        ReportDecisionLog(
            firm_id=current_user.firm_id,
            report_id=r.id,
            client_id=body.client_id or r.related_client_id,
            matter_id=body.matter_id or r.related_matter_id,
            reasonable_grounds=body.reasonable_grounds,
            reasoning=body.reasoning,
            decided_by_user_id=current_user.id,
        )
    )
    if not body.reasonable_grounds and r.status == "draft":
        r.status = "not_required"
    db.commit()
    db.refresh(r)
    return _report_out(r)


@router.post("/{report_id}/draft-narrative", response_model=ReportOut)
async def draft_narrative(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    """Ask Onus to draft the SMR 'grounds for suspicion' (a draft for human review)."""
    r = db.get(Report, report_id)
    if r is None or r.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    if r.type != "smr":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only SMRs have a narrative.")
    client = db.get(Client, r.related_client_id) if r.related_client_id else None
    matter = db.get(Matter, r.related_matter_id) if r.related_matter_id else None
    indicator = (r.payload or {}).get("indicator") or "suspicious activity"
    draft = await draft_smr_narrative(
        indicator=indicator,
        client_name=client.display_name if client else None,
        matter=matter.description if matter else None,
    )
    payload = dict(r.payload or {})
    payload["grounds_for_suspicion"] = draft
    r.payload = payload
    r.content_hash = _hash(payload)
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="report.ai_drafted",
            entity_type="report",
            entity_id=r.id,
        )
    )
    db.commit()
    db.refresh(r)
    return _report_out(r)


@records_router.get("", response_model=list[RecordOut])
def list_records(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RecordOut]:
    rows = db.scalars(
        select(Record).where(Record.firm_id == current_user.firm_id).order_by(Record.created_at.desc())
    ).all()
    return [
        RecordOut(
            id=r.id,
            category=r.category,
            entity_type=r.entity_type,
            retention_basis=r.retention_basis,
            basis_date=r.basis_date.isoformat() if r.basis_date else None,
            retention_until=r.retention_until.isoformat() if r.retention_until else None,
            immutable=r.immutable,
            created_at=r.created_at,
        )
        for r in rows
    ]
