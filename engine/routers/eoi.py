"""Demo expression of interest - a public lead-capture endpoint for demo visitors who
want a properly Australian-hosted deployment. Intentionally unauthenticated; stored in
the global demo_eois table (read it out of band, e.g. SELECT * FROM demo_eois)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import DemoEoi
from schemas import EoiIn

router = APIRouter()


@router.post("")
def submit_eoi(body: EoiIn, db: Session = Depends(get_db)) -> dict:
    db.add(
        DemoEoi(
            email=body.email,
            name=(body.name or None),
            firm_name=(body.firm_name or None),
            note=(body.note or None),
        )
    )
    db.commit()
    return {"status": "ok"}
