"""Demo expression of interest - a public lead-capture endpoint for demo visitors who
want a properly Australian-hosted deployment. Intentionally unauthenticated; stored in
the global demo_eois table. If Resend is configured (RESEND_API_KEY + EOI_NOTIFY_EMAIL),
each submission is also emailed; otherwise it is simply stored for you to read."""
from __future__ import annotations

import json
import os
import urllib.request

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import DemoEoi
from schemas import EoiIn

router = APIRouter()


def _notify(eoi: DemoEoi) -> None:
    """Email the submission via Resend if configured. Never raises - a notification
    failure must not fail the capture (the row is already stored)."""
    api_key = os.environ.get("RESEND_API_KEY")
    recipient = os.environ.get("EOI_NOTIFY_EMAIL")
    if not api_key or not recipient:
        return
    sender = os.environ.get("EOI_FROM_EMAIL", "onboarding@resend.dev")
    body = (
        f"New Onus demo expression of interest\n\n"
        f"Email: {eoi.email}\n"
        f"Name:  {eoi.name or '-'}\n"
        f"Firm:  {eoi.firm_name or '-'}\n"
        f"Note:  {eoi.note or '-'}\n"
    )
    payload = json.dumps(
        {"from": sender, "to": [recipient], "subject": "Onus demo - expression of interest", "text": body}
    ).encode()
    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass  # best-effort; the EOI is already persisted


@router.post("")
def submit_eoi(body: EoiIn, db: Session = Depends(get_db)) -> dict:
    eoi = DemoEoi(
        email=body.email,
        name=(body.name or None),
        firm_name=(body.firm_name or None),
        note=(body.note or None),
    )
    db.add(eoi)
    db.commit()
    db.refresh(eoi)
    _notify(eoi)
    return {"status": "ok"}
