import pytest

from auth.jwt import create_access_token, decode_access_token


def test_roundtrip(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    token = create_access_token(user_id="u1", firm_id="f1", role="admin", email="a@b.com")
    payload = decode_access_token(token)
    assert payload["user_id"] == "u1"
    assert payload["firm_id"] == "f1"
    assert payload["role"] == "admin"
    assert payload["email"] == "a@b.com"


def test_invalid_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    with pytest.raises(ValueError):
        decode_access_token("not-a-jwt")


def test_wrong_secret_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "secret-a")
    token = create_access_token(user_id="u1", firm_id="f1", role="admin", email="a@b.com")
    monkeypatch.setenv("JWT_SECRET", "secret-b")
    with pytest.raises(ValueError):
        decode_access_token(token)
