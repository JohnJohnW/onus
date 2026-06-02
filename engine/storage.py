"""Document storage. A small filesystem-backed store namespaced by firm, behind a
tiny interface so it can be swapped for S3/GCS later without touching callers.

Files are written under STORAGE_DIR/<firm_id>/<storage_key>, where storage_key is a
generated hex id (never a user-supplied name), so there is no path traversal and no
collision. The original filename is kept only as metadata on the Document row.
"""
from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

STORAGE_DIR = os.environ.get("STORAGE_DIR", "/data/documents")

# Reasonable caps for a compliance document store.
MAX_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff",
    ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".rtf", ".odt",
}

_KEY_RE = re.compile(r"^[0-9a-f]{32}$")


def is_allowed_filename(filename: str) -> bool:
    ext = Path(filename or "").suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def _firm_dir(firm_id) -> Path:
    path = Path(STORAGE_DIR) / str(firm_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_document(firm_id, data: bytes) -> str:
    """Write bytes and return the storage_key (relative to the firm's directory)."""
    key = uuid.uuid4().hex
    (_firm_dir(firm_id) / key).write_bytes(data)
    return key


def read_document(firm_id, storage_key: str) -> bytes:
    """Read a stored document. storage_key must be a generated hex id; reject anything
    else so a crafted value cannot escape the firm's directory."""
    if not _KEY_RE.match(storage_key or ""):
        raise ValueError("Invalid storage key.")
    path = Path(STORAGE_DIR) / str(firm_id) / storage_key
    return path.read_bytes()
