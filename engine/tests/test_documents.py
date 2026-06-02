"""Unit tests for the document storage layer: allowed types, save/read roundtrip,
and that a crafted storage key cannot escape the firm's directory."""
import uuid

import pytest

import storage


def test_allowed_filenames():
    assert storage.is_allowed_filename("passport.pdf")
    assert storage.is_allowed_filename("scan.JPG")  # case-insensitive
    assert storage.is_allowed_filename("register.xlsx")
    assert not storage.is_allowed_filename("evil.exe")
    assert not storage.is_allowed_filename("script.sh")
    assert not storage.is_allowed_filename("noextension")
    assert not storage.is_allowed_filename("")


def test_save_read_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_DIR", str(tmp_path))
    firm_id = uuid.uuid4()
    key = storage.save_document(firm_id, b"identity-document-bytes")
    assert storage.read_document(firm_id, key) == b"identity-document-bytes"


def test_two_firms_do_not_collide(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_DIR", str(tmp_path))
    a, b = uuid.uuid4(), uuid.uuid4()
    ka = storage.save_document(a, b"a")
    kb = storage.save_document(b, b"b")
    assert storage.read_document(a, ka) == b"a"
    assert storage.read_document(b, kb) == b"b"


def test_read_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "STORAGE_DIR", str(tmp_path))
    firm_id = uuid.uuid4()
    for bad_key in ("../../etc/passwd", "not-a-hex-key", "abc/def", ""):
        with pytest.raises(ValueError):
            storage.read_document(firm_id, bad_key)
