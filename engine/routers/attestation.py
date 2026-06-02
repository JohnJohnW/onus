"""Data-residency attestation - the firm's record of where its data is hosted and the
governance sign-off for that choice (see the README data-residency guidance). One row
per firm, upserted. Reading is open to any firm user; recording it is an admin action."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, require_admin
from database import get_db
from models import AuditLog, DataResidencyAttestation, User
from schemas import AttestationIn, AttestationOut

router = APIRouter()


def _current(db: Session, firm_id) -> Optional[DataResidencyAttestation]:
    return db.scalar(
        select(DataResidencyAttestation).where(DataResidencyAttestation.firm_id == firm_id)
    )


@router.get("", response_model=Optional[AttestationOut])
def get_attestation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[AttestationOut]:
    row = _current(db, current_user.firm_id)
    return AttestationOut.model_validate(row) if row is not None else None


@router.put("", response_model=AttestationOut)
def upsert_attestation(
    body: AttestationIn,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AttestationOut:
    attested_on = None
    if body.attested_on:
        try:
            attested_on = date.fromisoformat(body.attested_on)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date.")
        if attested_on > datetime.now(timezone.utc).date():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attestation date cannot be in the future.",
            )

    row = _current(db, current_user.firm_id)
    if row is None:
        row = DataResidencyAttestation(firm_id=current_user.firm_id, data_region=body.data_region)
        db.add(row)
    row.data_region = body.data_region
    row.hosting_provider = body.hosting_provider
    row.cross_border = body.cross_border
    row.dpa_in_place = body.dpa_in_place
    row.approved_by_name = body.approved_by_name
    row.attested_on = attested_on
    row.notes = body.notes
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="data_residency.attested",
            entity_type="firm",
            entity_id=current_user.firm_id,
            after_state={"data_region": body.data_region, "cross_border": body.cross_border},
        )
    )
    db.commit()
    db.refresh(row)
    return AttestationOut.model_validate(row)
