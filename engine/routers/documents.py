"""Document / evidence upload and retrieval (firm-scoped; retained per Act Pt 10).

The bytes live in the storage backend (storage.py); each Document row is the
firm-scoped metadata. Uploads are validated for type and size; downloads are served
as attachments and scoped to the caller's firm (RLS plus an explicit check)."""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import Document, User
from schemas import DocumentOut
from storage import MAX_BYTES, is_allowed_filename, read_document, save_document

router = APIRouter()

_ENTITY_TYPES = {"client", "party", "matter", "cdd_check", "evaluation", "report", "other"}


def _out(d: Document) -> DocumentOut:
    return DocumentOut(
        id=d.id,
        entity_type=d.entity_type,
        entity_id=d.entity_id,
        filename=d.filename,
        content_type=d.content_type,
        size_bytes=d.size_bytes,
        uploaded_by_user_id=d.uploaded_by_user_id,
        created_at=d.created_at,
    )


def _coerce_entity_id(entity_id: Optional[str]) -> Optional[uuid.UUID]:
    if not entity_id:
        return None
    try:
        return uuid.UUID(entity_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entity id.")


@router.post("", response_model=DocumentOut)
async def upload(
    file: UploadFile = File(...),
    entity_type: str = Form("other"),
    entity_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentOut:
    if entity_type not in _ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown entity type.")
    if not is_allowed_filename(file.filename or ""):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That file type is not allowed.")
    eid = _coerce_entity_id(entity_id)
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty.")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 20 MB).")
    key = save_document(current_user.firm_id, data)
    doc = Document(
        firm_id=current_user.firm_id,
        entity_type=entity_type,
        entity_id=eid,
        filename=(file.filename or "upload")[:255],
        content_type=file.content_type,
        size_bytes=len(data),
        storage_key=key,
        uploaded_by_user_id=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _out(doc)


@router.get("", response_model=List[DocumentOut])
def list_documents(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DocumentOut]:
    stmt = select(Document).where(Document.firm_id == current_user.firm_id)
    if entity_type:
        stmt = stmt.where(Document.entity_type == entity_type)
    eid = _coerce_entity_id(entity_id)
    if eid is not None:
        stmt = stmt.where(Document.entity_id == eid)
    rows = db.scalars(stmt.order_by(Document.created_at.desc())).all()
    return [_out(d) for d in rows]


@router.get("/{document_id}/download")
def download(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    d = db.get(Document, document_id)
    if d is None or d.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    try:
        data = read_document(d.firm_id, d.storage_key)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The document file is missing.")
    safe_name = d.filename.replace('"', "").replace("\n", " ").replace("\r", " ")
    # Always serve as an attachment so a stored file is never rendered/executed inline.
    return Response(
        content=data,
        media_type=d.content_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
