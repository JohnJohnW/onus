"""Integration tests: the real app against the real database. These verify that

  1. auth bootstrap (signup/login) still works once row-level security is enforced,
  2. firms are isolated from each other through the API, and
  3. RLS is actually enforced at the database (fails closed with no firm context),

so a future endpoint that forgets its firm filter cannot leak across tenants.

Skipped automatically when no database is reachable (e.g. a pure-unit CI runner
without Postgres); CI wires a Postgres service so they run there too.
"""
import uuid

import pytest
from sqlalchemy import text

from database import SessionLocal

try:
    _conn = SessionLocal()
    _conn.execute(text("SELECT 1"))
    _conn.close()
    _DB_AVAILABLE = True
except Exception:
    _DB_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _DB_AVAILABLE, reason="no database available")

PASSWORD = "password1234"  # schema requires >= 12 chars


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from main import app

    return TestClient(app)


def _signup(client, firm_name: str):
    email = f"it_{uuid.uuid4().hex[:10]}@test.local"
    res = client.post(
        "/auth/signup",
        json={"firm_name": firm_name, "full_name": "Principal", "email": email, "password": PASSWORD},
    )
    assert res.status_code == 200, res.text
    return email, res.json()["access_token"]


def test_signup_login_me_survive_rls(client):
    """Signup writes firm-scoped rows (governance role, risk state) under RLS; if the
    GUC wiring were wrong this would fail closed."""
    email, token = _signup(client, "Integration Firm")
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


def test_login_rejects_wrong_password(client):
    email, _ = _signup(client, "Integration Firm 2")
    res = client.post("/auth/login", json={"email": email, "password": "totally-wrong-1"})
    assert res.status_code == 401


def test_unauthenticated_requests_are_rejected(client):
    assert client.get("/clients").status_code in (401, 403)


def test_authed_write_then_read_works(client):
    """A firm can create and read back its own client (RLS WITH CHECK + USING)."""
    _, token = _signup(client, "Solo Firm")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/clients", json={"type": "company_domestic", "display_name": "Own Client Pty Ltd"}, headers=headers
    )
    assert created.status_code in (200, 201), created.text
    listing = client.get("/clients", headers=headers)
    assert listing.status_code == 200
    assert any(c["id"] == created.json()["id"] for c in listing.json())


def test_cross_tenant_isolation(client):
    _, token_a = _signup(client, "Firm A")
    _, token_b = _signup(client, "Firm B")
    head_a = {"Authorization": f"Bearer {token_a}"}
    head_b = {"Authorization": f"Bearer {token_b}"}

    created = client.post(
        "/clients", json={"type": "company_domestic", "display_name": "ACME Pty Ltd"}, headers=head_a
    )
    assert created.status_code in (200, 201), created.text
    client_id = created.json()["id"]

    a_ids = {c["id"] for c in client.get("/clients", headers=head_a).json()}
    b_ids = {c["id"] for c in client.get("/clients", headers=head_b).json()}
    assert client_id in a_ids, "Firm A should see its own client"
    assert client_id not in b_ids, "Firm B must not see Firm A's client"

    # A direct fetch by id from the other firm must 404 (no cross-tenant read).
    assert client.get(f"/clients/{client_id}", headers=head_b).status_code == 404


def test_matter_classification_populates_agent_feed(client, monkeypatch):
    """The classify endpoint runs the AI (mock here), returns a draft suggestion, and
    records an AgentTask that shows up in the dashboard 'Onus activity' feed."""
    monkeypatch.setenv("AI_PROVIDER", "mock")  # deterministic; no real API call
    _, token = _signup(client, "Classify Firm")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        "/matters/classify",
        json={"description": "acting for the buyer in a residential property purchase"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert "rationale" in res.json()

    summary = client.get("/dashboard/summary", headers=headers)
    assert summary.status_code == 200
    activity = summary.json().get("recent_agent_activity", [])
    assert any("matter" in a["summary"].lower() for a in activity), activity


def test_document_upload_list_download_and_isolation(client):
    """Upload an evidence file, list and download it, and confirm another firm can
    neither see nor download it; disallowed file types are rejected."""
    _, token_a = _signup(client, "Doc Firm A")
    _, token_b = _signup(client, "Doc Firm B")
    head_a = {"Authorization": f"Bearer {token_a}"}
    head_b = {"Authorization": f"Bearer {token_b}"}

    up = client.post(
        "/documents",
        files={"file": ("evidence.pdf", b"%PDF-1.4 evidence", "application/pdf")},
        data={"entity_type": "client"},
        headers=head_a,
    )
    assert up.status_code == 200, up.text
    doc_id = up.json()["id"]

    a_ids = {d["id"] for d in client.get("/documents", headers=head_a).json()}
    b_ids = {d["id"] for d in client.get("/documents", headers=head_b).json()}
    assert doc_id in a_ids
    assert doc_id not in b_ids  # firm B cannot see firm A's document

    dl = client.get(f"/documents/{doc_id}/download", headers=head_a)
    assert dl.status_code == 200
    assert dl.content == b"%PDF-1.4 evidence"
    assert "attachment" in dl.headers.get("content-disposition", "")

    assert client.get(f"/documents/{doc_id}/download", headers=head_b).status_code == 404

    bad = client.post(
        "/documents",
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
        data={"entity_type": "client"},
        headers=head_a,
    )
    assert bad.status_code == 400


def _firm_id(token: str) -> str:
    from jose import jwt as jose_jwt

    return jose_jwt.get_unverified_claims(token)["firm_id"]


def test_manual_deadline_completion(client):
    _, token = _signup(client, "Deadline Firm")
    headers = {"Authorization": f"Bearer {token}"}
    fid = _firm_id(token)
    # Marking enrolment in progress creates the enrolment deadline.
    assert client.patch(f"/firms/{fid}", json={"enrolment_status": "in_progress"}, headers=headers).status_code == 200
    deadlines = client.get("/dashboard/summary", headers=headers).json()["upcoming_deadlines"]
    enrol = next((d for d in deadlines if "nrol" in d["name"]), None)
    assert enrol is not None, deadlines
    assert client.post(f"/dashboard/deadlines/{enrol['id']}/complete", headers=headers).status_code == 200
    after = client.get("/dashboard/summary", headers=headers).json()["upcoming_deadlines"]
    assert all(d["id"] != enrol["id"] for d in after)


def test_enrolment_deadline_auto_completes(client):
    _, token = _signup(client, "Enrol Firm")
    headers = {"Authorization": f"Bearer {token}"}
    fid = _firm_id(token)
    client.patch(f"/firms/{fid}", json={"enrolment_status": "in_progress"}, headers=headers)
    before = client.get("/dashboard/summary", headers=headers).json()["upcoming_deadlines"]
    assert any("nrol" in d["name"] for d in before)
    client.patch(
        f"/firms/{fid}",
        json={"enrolment_status": "enrolled", "austrac_enrolment_number": "100000123"},
        headers=headers,
    )
    after = client.get("/dashboard/summary", headers=headers).json()["upcoming_deadlines"]
    assert not any("nrol" in d["name"] for d in after)


def test_review_trigger_resolution(client):
    _, token = _signup(client, "Trigger Firm")
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/program/triggers",
        json={"trigger_type": "significant_change", "description": "New service line"},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    tid = created.json()["id"]
    open_ids = {t["id"] for t in client.get("/program/lifecycle", headers=headers).json()["open_triggers"]}
    assert tid in open_ids
    assert client.post(f"/program/triggers/{tid}/resolve", headers=headers).status_code == 200
    open_after = {t["id"] for t in client.get("/program/lifecycle", headers=headers).json()["open_triggers"]}
    assert tid not in open_after


def test_rls_fails_closed_without_firm_context():
    """At the database, with no app.current_firm_id set, RLS returns zero firm-scoped
    rows even though the app connects as the table owner (FORCE ROW LEVEL SECURITY).
    This is the backstop: a query that forgets its firm filter sees nothing, not
    another tenant's data."""
    db = SessionLocal()
    try:
        for table in ("clients", "reports", "matters", "risk_assessments"):
            count = db.execute(text(f"SELECT count(*) FROM {table}")).scalar()
            assert count == 0, f"{table} leaked {count} rows with no firm context"
    finally:
        db.close()
