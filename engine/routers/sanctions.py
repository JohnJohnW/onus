"""Sanctions screening against the DFAT Consolidated List (Rules s5-3).

The list is global reference data, ingested as versioned snapshots (auto-fetched
from DFAT or uploaded manually). Screening surfaces candidate matches for a human
to adjudicate; Onus never auto-clears or auto-blocks. Each screening can be
recorded for the audit trail, noting exactly which list version was used.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import SanctionsEntry, SanctionsListVersion, SanctionsScreening, User
from sanctions.ingest import import_version, parse_csv, parse_xlsx, rows_to_entries
from sanctions.matching import DEFAULT_THRESHOLD
from sanctions.matching import screen as run_screen
from schemas import SanctionsStatusOut, ScreenRequest, ScreenResultOut

router = APIRouter()

SOURCE = "dfat_consolidated"
DEFAULT_DFAT_URL = "https://www.dfat.gov.au/sites/default/files/regulation8_consolidated.xlsx"


def _list_url() -> str:
    return os.getenv("DFAT_CONSOLIDATED_LIST_URL", DEFAULT_DFAT_URL)


def _current(db: Session) -> Optional[SanctionsListVersion]:
    return db.scalar(
        select(SanctionsListVersion).where(
            SanctionsListVersion.source == SOURCE,
            SanctionsListVersion.is_current.is_(True),
        )
    )


def _status(db: Session) -> SanctionsStatusOut:
    v = _current(db)
    return SanctionsStatusOut(
        loaded=v is not None,
        source=v.source if v else None,
        origin=v.origin if v else None,
        fetched_at=v.fetched_at if v else None,
        entry_count=v.entry_count if v else 0,
        content_hash=v.content_hash if v else None,
        url_configured=bool(_list_url()),
    )


@router.get("/status", response_model=SanctionsStatusOut)
def get_status(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SanctionsStatusOut:
    return _status(db)


@router.post("/refresh", response_model=SanctionsStatusOut)
async def refresh(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SanctionsStatusOut:
    """Auto-fetch the latest DFAT Consolidated List from the configured URL."""
    url = _list_url()
    if not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No DFAT list URL configured.")
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.content
    except Exception as exc:  # network/HTTP failure -> manual upload is the fallback
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch the DFAT list ({exc}). You can upload the file manually instead.",
        )
    try:
        entries = rows_to_entries(parse_xlsx(content))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Could not parse the list: {exc}")
    if not entries:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No entries found in the fetched file.")
    import_version(db, source=SOURCE, origin="auto_fetch", entries=entries, note="Auto-fetched from DFAT")
    return _status(db)


@router.post("/upload", response_model=SanctionsStatusOut)
async def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SanctionsStatusOut:
    """Manual fallback: upload a DFAT Consolidated List file (.xlsx or .csv)."""
    content = await file.read()
    name = (file.filename or "").lower()
    try:
        if name.endswith(".csv"):
            rows = parse_csv(content.decode("utf-8-sig", errors="replace"))
        elif name.endswith(".xlsx"):
            rows = parse_xlsx(content)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload a .xlsx or .csv file.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Could not parse the file: {exc}")
    entries = rows_to_entries(rows)
    if not entries:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No recognisable entries in the file.")
    import_version(db, source=SOURCE, origin="manual_upload", entries=entries, note=f"Uploaded {file.filename}")
    return _status(db)


@router.post("/screen", response_model=ScreenResultOut)
def screen(
    body: ScreenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScreenResultOut:
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A name is required to screen.")
    version = _current(db)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No sanctions list is loaded. Load the DFAT list (refresh or upload) first.",
        )
    rows = db.scalars(select(SanctionsEntry).where(SanctionsEntry.version_id == version.id)).all()
    entries = [
        {
            "reference": e.reference,
            "entity_type": e.entity_type,
            "primary_name": e.primary_name,
            "search_names": e.search_names or [],
            "aliases": e.aliases or [],
            "dob": e.dob,
            "citizenship": e.citizenship,
            "listing_info": e.listing_info,
        }
        for e in rows
    ]
    threshold = body.threshold if body.threshold is not None else DEFAULT_THRESHOLD
    matches = run_screen(name, entries, threshold)[:50]
    candidates = [
        {
            "reference": m.get("reference"),
            "entity_type": m["entity_type"],
            "primary_name": m["primary_name"],
            "matched_name": m["matched_name"],
            "score": m["score"],
            "aliases": m.get("aliases"),
            "dob": m.get("dob"),
            "citizenship": m.get("citizenship"),
            "listing_info": m.get("listing_info"),
        }
        for m in matches
    ]
    if body.record:
        db.add(
            SanctionsScreening(
                firm_id=current_user.firm_id,
                subject_type=body.subject_type,
                subject_id=body.subject_id,
                query_name=name,
                version_id=version.id,
                match_count=len(candidates),
                top_score=candidates[0]["score"] if candidates else None,
                matches=candidates,
                screened_by_user_id=current_user.id,
            )
        )
        db.commit()
    return ScreenResultOut(
        query_name=name,
        list_fetched_at=version.fetched_at,
        match_count=len(candidates),
        candidates=candidates,
    )
