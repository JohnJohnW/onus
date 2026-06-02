"""Sanctions and PEP screening (AML/CTF Rules s5-3 sanctions; s5-5 PEPs).

Both are list-based: a list is ingested as versioned snapshots (auto-fetched or
uploaded), and a name is matched against the current snapshot of a list_type
(sanctions | pep). The same ingestion, versioning and matcher serve both; only the
data source differs. Screening surfaces candidates for a human to adjudicate - Onus
never auto-clears or auto-blocks. Adverse-media has no authoritative list, so it
stays a documented manual check, not a faked list here.
"""
from __future__ import annotations

import os
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_log import record_agent_task
from auth.dependencies import get_current_user, require_admin
from database import get_db
from models import SanctionsEntry, SanctionsListVersion, SanctionsScreening, User
from sanctions.ingest import import_version, parse_csv, parse_xlsx, rows_to_entries
from sanctions.matching import DEFAULT_THRESHOLD
from sanctions.matching import screen as run_screen
from schemas import SanctionsStatusOut, ScreenRequest, ScreenResultOut

router = APIRouter()

DEFAULT_DFAT_URL = "https://www.dfat.gov.au/sites/default/files/regulation8_consolidated.xlsx"

# list_type -> (default source name, env var for the fetch URL, built-in default URL, label)
_LISTS = {
    "sanctions": ("dfat_consolidated", "DFAT_CONSOLIDATED_LIST_URL", DEFAULT_DFAT_URL, "sanctions"),
    "pep": ("pep_list", "OPENSANCTIONS_PEP_URL", "", "PEP"),
}


def _config(list_type: str):
    cfg = _LISTS.get(list_type)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown list type.")
    return cfg


def _list_url(list_type: str) -> str:
    _source, env_var, default_url, _label = _config(list_type)
    return os.getenv(env_var, default_url)


def _current(db: Session, list_type: str) -> Optional[SanctionsListVersion]:
    return db.scalar(
        select(SanctionsListVersion).where(
            SanctionsListVersion.list_type == list_type,
            SanctionsListVersion.is_current.is_(True),
        )
    )


def _status(db: Session, list_type: str) -> SanctionsStatusOut:
    v = _current(db, list_type)
    return SanctionsStatusOut(
        list_type=list_type,
        loaded=v is not None,
        source=v.source if v else None,
        origin=v.origin if v else None,
        fetched_at=v.fetched_at if v else None,
        entry_count=v.entry_count if v else 0,
        content_hash=v.content_hash if v else None,
        url_configured=bool(_list_url(list_type)),
    )


@router.get("/status", response_model=SanctionsStatusOut)
def get_status(
    list_type: str = Query("sanctions"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SanctionsStatusOut:
    _config(list_type)
    return _status(db, list_type)


@router.post("/refresh", response_model=SanctionsStatusOut)
async def refresh(
    list_type: str = Query("sanctions"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SanctionsStatusOut:
    """Auto-fetch the latest list from the configured URL (sanctions: DFAT). Admin only:
    the list is global, shared by every firm, so ingestion must not be a member action."""
    source, _env, _default, label = _config(list_type)
    url = _list_url(list_type)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No {label} list URL is configured. Upload the file manually instead.",
        )
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.content
    except Exception as exc:  # network/HTTP failure -> manual upload is the fallback
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch the {label} list ({exc}). You can upload it manually instead.",
        )
    try:
        entries = rows_to_entries(parse_xlsx(content))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Could not parse the list: {exc}")
    if not entries:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No entries found in the fetched file.")
    import_version(db, source=source, origin="auto_fetch", entries=entries, list_type=list_type, note=f"Auto-fetched {label}")
    return _status(db, list_type)


@router.post("/upload", response_model=SanctionsStatusOut)
async def upload(
    file: UploadFile = File(...),
    list_type: str = Form("sanctions"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SanctionsStatusOut:
    """Manual fallback: upload a list file (.xlsx or .csv) for sanctions or PEP. Admin
    only - the list is global reference data shared across firms."""
    source, _env, _default, _label = _config(list_type)
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
    import_version(db, source=source, origin="manual_upload", entries=entries, list_type=list_type, note=f"Uploaded {file.filename}")
    return _status(db, list_type)


@router.post("/screen", response_model=ScreenResultOut)
def screen(
    body: ScreenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScreenResultOut:
    list_type = body.list_type or "sanctions"
    _source, _env, _default, label = _config(list_type)
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A name is required to screen.")
    version = _current(db, list_type)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No {label} list is loaded. Load it (refresh or upload) first.",
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
                list_type=list_type,
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
        record_agent_task(
            db,
            current_user.firm_id,
            task_type=f"{list_type}_screened",
            summary=(
                f"Screened \"{name}\" against the {label} list: {len(candidates)} potential match"
                f"{'' if len(candidates) == 1 else 'es'}"
            ),
            human_action_required=len(candidates) > 0,
            human_action_type=f"review_{list_type}_matches" if candidates else None,
            input_state={"query_name": name, "list_type": list_type},
        )
        db.commit()
    return ScreenResultOut(
        query_name=name,
        list_type=list_type,
        list_fetched_at=version.fetched_at,
        match_count=len(candidates),
        candidates=candidates,
    )
