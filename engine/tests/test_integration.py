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


def test_refresh_issues_a_valid_token_for_same_user(client):
    """An authenticated caller can exchange a valid token for a fresh one that still
    identifies the same user - this is what keeps an active session from lapsing
    mid-use without a re-login."""
    email, token = _signup(client, "Refresh Firm")
    res = client.post("/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    new_token = res.json()["access_token"]
    assert new_token
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {new_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == email


def test_login_throttles_repeated_failures(client):
    """Repeated wrong-password attempts on one account lock it out (429). The lock is by
    account, so even the correct password is refused during the cooldown window."""
    email, _ = _signup(client, "Throttle Firm")
    codes = [
        client.post(
            "/auth/login", json={"email": email, "password": "definitely-the-wrong-1"}
        ).status_code
        for _ in range(12)
    ]
    assert 429 in codes, codes
    # Locked by account: the correct password is also refused until the window passes.
    assert (
        client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 429
    )


def test_refresh_rejects_unauthenticated(client):
    """Refresh is a rolling renewal for a valid session, not a way to mint a token
    without credentials."""
    assert client.post("/auth/refresh").status_code in (401, 403)
    assert client.post("/auth/refresh", headers={"Authorization": "Bearer not.a.token"}).status_code == 401


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


def test_risk_summary_draft_populates_agent_feed(client, monkeypatch):
    """Onus drafts the risk-assessment summary (mock AI), saves it as a draft, and records
    an AgentTask in the activity feed. It must not approve the assessment."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    _, token = _signup(client, "Risk Draft Firm")
    h = {"Authorization": f"Bearer {token}"}
    client.post("/risk-assessment/services", json={"services": ["Property transactions"]}, headers=h)
    res = client.post("/risk-assessment/draft-summary", headers=h)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["summary"], body
    assert body["status"] == "draft"  # a draft - Onus did not approve it
    activity = client.get("/dashboard/summary", headers=h).json().get("recent_agent_activity", [])
    assert any("risk" in a["summary"].lower() for a in activity), activity


def test_cdd_plan_drafted_by_onus(client, monkeypatch):
    """Onus prepares a CDD plan (mock AI): returns the required level + a drafted plan,
    records an AgentTask, and does not complete or sign off CDD."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    _, token = _signup(client, "CDD Plan Firm")
    h = {"Authorization": f"Bearer {token}"}
    cid = client.post(
        "/clients", json={"type": "company_domestic", "display_name": "Acme Pty Ltd"}, headers=h
    ).json()["id"]
    res = client.post(f"/clients/{cid}/cdd-plan", headers=h)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["level"] in ("simplified", "standard", "enhanced")
    assert body["plan"]
    # Onus did not complete CDD - the client's CDD status is unchanged.
    detail = client.get(f"/clients/{cid}", headers=h).json()
    assert detail["cdd_status"] == "not_started", detail
    activity = client.get("/dashboard/summary", headers=h).json().get("recent_agent_activity", [])
    assert any("cdd" in a["summary"].lower() for a in activity), activity


def test_risk_assessment_docx_download(client):
    """The risk assessment downloads as a real .docx (submission-ready document)."""
    _, token = _signup(client, "Docx Firm")
    h = {"Authorization": f"Bearer {token}"}
    client.post("/risk-assessment/services", json={"services": ["Property transactions"]}, headers=h)
    res = client.get("/risk-assessment/document", headers=h)
    assert res.status_code == 200, res.text
    assert (
        res.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert res.content[:2] == b"PK", res.content[:8]  # .docx is a zip archive


def test_evaluation_docx_download(client):
    """The independent evaluation downloads as a real .docx."""
    _, token = _signup(client, "Eval Docx Firm")
    h = {"Authorization": f"Bearer {token}"}
    eid = client.post("/evaluations", json={}, headers=h).json()["id"]
    res = client.get(f"/evaluations/{eid}/document", headers=h)
    assert res.status_code == 200, res.text
    assert res.content[:2] == b"PK", res.content[:8]


def test_program_docx_download(client):
    """The compliance program downloads as a real .docx."""
    _, token = _signup(client, "Program Docx Firm")
    h = {"Authorization": f"Bearer {token}"}
    res = client.get("/program/document", headers=h)
    assert res.status_code == 200, res.text
    assert res.content[:2] == b"PK", res.content[:8]


def test_smr_docx_download(client):
    """An SMR downloads as a real .docx with the prepared content."""
    _, token = _signup(client, "SMR Docx Firm")
    h = {"Authorization": f"Bearer {token}"}
    rid = client.post(
        "/reports",
        json={
            "type": "smr",
            "payload": {
                "indicator": "structuring",
                "grounds_for_suspicion": "Cash deposits just under the threshold.",
            },
        },
        headers=h,
    ).json()["id"]
    res = client.get(f"/reports/{rid}/document", headers=h)
    assert res.status_code == 200, res.text
    assert res.content[:2] == b"PK", res.content[:8]


def test_document_analysis_returns_extraction(client, monkeypatch):
    """Onus reads an uploaded document (mock AI), returns an analysis, and logs the action.
    The document is not stored by Onus (analysis is transient)."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    _, token = _signup(client, "Analyze Doc Firm")
    h = {"Authorization": f"Bearer {token}"}
    files = {"file": ("extract.pdf", b"%PDF-1.4 ACME PTY LTD director Jane Doe 60 percent", "application/pdf")}
    res = client.post(
        "/documents/analyze", data={"purpose": "beneficial_owners"}, files=files, headers=h
    )
    assert res.status_code == 200, res.text
    assert res.json()["analysis"]
    activity = client.get("/dashboard/summary", headers=h).json().get("recent_agent_activity", [])
    assert any("analyz" in a["summary"].lower() for a in activity), activity


def test_document_extracts_beneficial_owners(client, monkeypatch):
    """The beneficial-owners purpose returns structured owners (for one-click add)."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    _, token = _signup(client, "BO Extract Firm")
    h = {"Authorization": f"Bearer {token}"}
    files = {"file": ("extract.pdf", b"%PDF-1.4 ACME PTY LTD director Jane Doe 60 percent", "application/pdf")}
    res = client.post(
        "/documents/analyze", data={"purpose": "beneficial_owners"}, files=files, headers=h
    )
    assert res.status_code == 200, res.text
    owners = res.json()["owners"]
    assert owners and owners[0]["name"] == "Jane Doe", owners


def test_agent_review_disabled_by_default(client):
    """The managed-agent review is off unless MANAGED_AGENTS_ENABLED is set."""
    _, token = _signup(client, "No Managed Firm")
    h = {"Authorization": f"Bearer {token}"}
    res = client.post("/risk-assessment/agent-review", headers=h)
    assert res.status_code == 400, res.text


def test_agent_review_managed_mock(client, monkeypatch):
    """With the flag on and the mock provider, the cloud-session flow starts and polls to a
    done review note - covers the orchestration without the live beta platform."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("MANAGED_AGENTS_ENABLED", "true")
    _, token = _signup(client, "Agent Review Firm")
    h = {"Authorization": f"Bearer {token}"}
    client.post("/risk-assessment/services", json={"services": ["Property transactions"]}, headers=h)
    start = client.post("/risk-assessment/agent-review", headers=h)
    assert start.status_code == 200, start.text
    sid = start.json()["session_id"]
    res = client.get(f"/risk-assessment/agent-review/{sid}", headers=h)
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "done"
    assert res.json()["note"]


def test_risk_review_note(client, monkeypatch):
    """Onus runs a periodic review and returns a note; the action is logged."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    _, token = _signup(client, "Review Note Firm")
    h = {"Authorization": f"Bearer {token}"}
    client.post("/risk-assessment/services", json={"services": ["Property transactions"]}, headers=h)
    res = client.post("/risk-assessment/review", headers=h)
    assert res.status_code == 200, res.text
    assert res.json()["note"]
    activity = client.get("/dashboard/summary", headers=h).json().get("recent_agent_activity", [])
    assert any("review" in a["summary"].lower() for a in activity), activity


def test_document_extracts_source_of_funds(client, monkeypatch):
    """The source-of-funds purpose returns a statement to save on the client file."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    _, token = _signup(client, "SoF Firm")
    h = {"Authorization": f"Bearer {token}"}
    files = {"file": ("statement.pdf", b"%PDF salary deposits from employer Acme", "application/pdf")}
    res = client.post(
        "/documents/analyze", data={"purpose": "source_of_funds"}, files=files, headers=h
    )
    assert res.status_code == 200, res.text
    assert res.json()["source_of_funds"]


def test_document_extracts_identity(client, monkeypatch):
    """The identity purpose returns structured ID details (for one-click CDD record)."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    _, token = _signup(client, "ID Extract Firm")
    h = {"Authorization": f"Bearer {token}"}
    files = {"file": ("id.jpg", b"\xff\xd8\xff fake-jpeg-bytes", "image/jpeg")}
    res = client.post("/documents/analyze", data={"purpose": "identity"}, files=files, headers=h)
    assert res.status_code == 200, res.text
    ident = res.json()["identity"]
    assert ident and ident["full_name"] == "Jane Doe", ident


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


def test_user_management_and_role_enforcement(client):
    _, admin_token = _signup(client, "Team Firm")
    admin_h = {"Authorization": f"Bearer {admin_token}"}

    member_email = f"mem_{uuid.uuid4().hex[:8]}@test.local"
    created = client.post(
        "/firms/users",
        json={"full_name": "Mem Ber", "email": member_email, "role": "member"},
        headers=admin_h,
    )
    assert created.status_code == 200, created.text
    temp = created.json()["temporary_password"]
    assert temp and created.json()["user"]["role"] == "member"

    login = client.post("/auth/login", json={"email": member_email, "password": temp})
    assert login.status_code == 200
    member_h = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # A member is gated from admin actions and from approving.
    blocked = client.post(
        "/firms/users",
        json={"full_name": "X", "email": "x@test.local", "role": "member"},
        headers=member_h,
    )
    assert blocked.status_code == 403
    assert client.post("/risk-assessment/approve", headers=member_h).status_code == 403
    # The admin is not gated (no RA yet -> not 403).
    assert client.post("/risk-assessment/approve", headers=admin_h).status_code != 403


def test_change_password(client):
    email, token = _signup(client, "Password Firm")
    headers = {"Authorization": f"Bearer {token}"}
    changed = client.post(
        "/auth/change-password",
        json={"current_password": "password1234", "new_password": "a-brand-new-pass-9"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "a-brand-new-pass-9"}).status_code == 200
    assert client.post("/auth/login", json={"email": email, "password": "password1234"}).status_code == 401


def test_cannot_demote_self(client):
    from jose import jwt as jose_jwt

    _, token = _signup(client, "Solo Admin Firm")
    headers = {"Authorization": f"Bearer {token}"}
    uid = jose_jwt.get_unverified_claims(token)["user_id"]
    assert client.patch(f"/firms/users/{uid}", json={"role": "member"}, headers=headers).status_code == 400


def test_governance_role_unique_constraint(client):
    """The DB rejects a second row for the same (firm, role) - no duplicate officers."""
    from sqlalchemy.exc import IntegrityError

    from database import SessionLocal, set_session_firm
    from models import GovernanceRole

    _, token = _signup(client, "Unique Role Firm")
    fid = _firm_id(token)
    db = SessionLocal()
    try:
        set_session_firm(db, fid)
        db.add(GovernanceRole(firm_id=fid, role="senior_manager"))
        db.commit()
        db.add(GovernanceRole(firm_id=fid, role="senior_manager"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_pep_screening_is_a_separate_list(client):
    """PEP uses the same screening infrastructure under a distinct list_type, so a
    PEP list can be loaded and screened independently of the sanctions list."""
    from sqlalchemy import select

    from database import SessionLocal
    from models import SanctionsListVersion

    _, token = _signup(client, "PEP Firm")
    headers = {"Authorization": f"Bearer {token}"}

    up = client.post(
        "/sanctions/upload",
        files={
            "file": (
                "pep.csv",
                b"Reference,Name of Individual or Entity,Type,Position\nP1,Jane Official,Individual,Minister\n",
                "text/csv",
            )
        },
        data={"list_type": "pep"},
        headers=headers,
    )
    assert up.status_code == 200, up.text
    assert up.json()["list_type"] == "pep" and up.json()["loaded"]

    pep_status = client.get("/sanctions/status?list_type=pep", headers=headers).json()
    assert pep_status["loaded"] and pep_status["entry_count"] == 1

    # Screen against PEP (record=False so no screening row pins the version for cleanup).
    screened = client.post(
        "/sanctions/screen",
        json={"name": "Jane Official", "list_type": "pep", "record": False},
        headers=headers,
    ).json()
    assert screened["list_type"] == "pep"
    assert screened["match_count"] == 1

    # Clean up the global PEP list so it doesn't leak into other firms' views.
    db = SessionLocal()
    try:
        for v in db.scalars(
            select(SanctionsListVersion).where(SanctionsListVersion.list_type == "pep")
        ).all():
            db.delete(v)
        db.commit()
    finally:
        db.close()


def test_annual_compliance_summary(client):
    _, token = _signup(client, "Annual Firm")
    headers = {"Authorization": f"Bearer {token}"}
    summary = client.get("/reports/annual-summary", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert "period_start" in body and "period_end" in body
    assert body["smr_lodged"] == 0  # a fresh firm has nothing lodged yet
    # Creating an annual report snapshots the summary into its payload.
    rep = client.post("/reports", json={"type": "annual_compliance"}, headers=headers)
    assert rep.status_code == 200


def test_automated_monitoring_scan(client):
    _, token = _signup(client, "Scan Firm")
    headers = {"Authorization": f"Bearer {token}"}
    cid = client.post(
        "/clients",
        json={"type": "company_domestic", "display_name": "Risky Co", "sanctions_hit": True},
        headers=headers,
    ).json()["id"]
    client.post("/matters", json={"client_id": cid, "designated_service_key": "T6_1"}, headers=headers)

    first = client.post("/alerts/scan", headers=headers).json()
    assert first["raised"] >= 1
    assert any(a["indicator_key"] == "sanctions_flagged_active" for a in first["alerts"])

    # Running again raises nothing new (open findings are de-duplicated).
    second = client.post("/alerts/scan", headers=headers).json()
    assert second["raised"] == 0


def test_alert_state_guards_and_report_status_validation(client):
    _, token = _signup(client, "Guards Firm")
    h = {"Authorization": f"Bearer {token}"}
    cid = client.post("/clients", json={"type": "company_domestic", "display_name": "Guard Co"}, headers=h).json()["id"]
    al = client.post("/alerts", json={"client_id": cid, "indicator_key": "structuring", "severity": "high"}, headers=h)
    assert al.status_code in (200, 201), al.text
    aid = al.json()["id"]
    esc = client.post(f"/alerts/{aid}/escalate", json={}, headers=h)
    assert esc.status_code == 200
    # An escalated alert cannot be dismissed (would orphan the SMR).
    assert client.post(f"/alerts/{aid}/dismiss", json={}, headers=h).status_code == 409
    # The SMR created by escalation rejects an invalid status.
    smr_id = esc.json()["smr_report_id"]
    assert client.patch(f"/reports/{smr_id}", json={"status": "cancelled"}, headers=h).status_code == 400


def test_member_cannot_load_sanctions_list(client):
    _, admin_token = _signup(client, "List Admin Firm")
    ah = {"Authorization": f"Bearer {admin_token}"}
    created = client.post(
        "/firms/users",
        json={"full_name": "Mem", "email": f"lm_{uuid.uuid4().hex[:8]}@test.local", "role": "member"},
        headers=ah,
    )
    temp = created.json()["temporary_password"]
    mtok = client.post(
        "/auth/login", json={"email": created.json()["user"]["email"], "password": temp}
    ).json()["access_token"]
    mh = {"Authorization": f"Bearer {mtok}"}
    # A member cannot overwrite the global sanctions list.
    res = client.post(
        "/sanctions/upload",
        files={"file": ("x.csv", b"Reference,Name of Individual or Entity,Type\n1,X,Entity\n", "text/csv")},
        data={"list_type": "sanctions"},
        headers=mh,
    )
    assert res.status_code == 403


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


def test_risk_overall_recomputed_on_services(client):
    """Adding a high-risk service must lift the overall rating immediately. It used to
    stay 'unassessed' because only the /countries endpoint recomputed the overall."""
    _, token = _signup(client, "Recompute Firm")
    h = {"Authorization": f"Bearer {token}"}
    assert (
        client.post(
            "/risk-assessment/services", json={"services": ["Trust establishment"]}, headers=h
        ).status_code
        == 200
    )
    cur = client.get("/risk-assessment/current", headers=h).json()
    assert cur["overall_rating"] == "high", cur


def test_cdd_rejects_unknown_matter_with_404(client):
    """A non-existent matter id must be a clean 404, not a foreign-key violation 500."""
    _, token = _signup(client, "CDD 404 Firm")
    h = {"Authorization": f"Bearer {token}"}
    client_id = client.post(
        "/clients", json={"type": "company_domestic", "display_name": "C"}, headers=h
    ).json()["id"]
    res = client.post(
        f"/clients/{client_id}/cdd",
        json={"matter_id": "00000000-0000-0000-0000-000000000000"},
        headers=h,
    )
    assert res.status_code == 404, res.text


def test_methodology_rejects_invalid_complexity_tier(client):
    _, token = _signup(client, "Methodology Firm")
    h = {"Authorization": f"Bearer {token}"}
    res = client.post(
        "/risk-assessment/methodology",
        json={"methodology": "impact_only", "complexity_tier": "nonsense"},
        headers=h,
    )
    assert res.status_code == 400, res.text


def test_policy_status_rejects_invalid_value(client):
    _, token = _signup(client, "Policy Status Firm")
    h = {"Authorization": f"Bearer {token}"}
    policy_id = client.get("/program", headers=h).json()["policies"][0]["id"]
    res = client.patch(f"/program/policies/{policy_id}", json={"status": "nonsense"}, headers=h)
    assert res.status_code == 400, res.text


def test_program_records_admin_approver_role(client):
    """When an admin approves, the s26P audit trail must record 'admin', not a fixed
    'senior_manager' label."""
    _, token = _signup(client, "Approver Role Firm")
    h = {"Authorization": f"Bearer {token}"}
    res = client.post("/program/approve", json={}, headers=h)
    assert res.status_code == 200, res.text
    assert res.json()["approved_by_role"] == "admin", res.json()


def test_signup_rejects_invalid_email(client):
    res = client.post(
        "/auth/signup",
        json={"firm_name": "Bad Email", "full_name": "X", "email": "notanemail", "password": PASSWORD},
    )
    assert res.status_code == 422, res.text


def test_onboarding_complete_is_idempotent(client):
    """A repeated /onboarding/complete must not duplicate the standing deadlines."""
    _, token = _signup(client, "Idempotent Onboarding Firm")
    h = {"Authorization": f"Bearer {token}"}
    client.post("/risk-assessment/services", json={"services": ["Property transactions"]}, headers=h)
    assert client.post("/onboarding/complete", headers=h).status_code == 200
    first = len(client.get("/dashboard/summary", headers=h).json()["upcoming_deadlines"])
    assert client.post("/onboarding/complete", headers=h).status_code == 200
    second = len(client.get("/dashboard/summary", headers=h).json()["upcoming_deadlines"])
    assert second == first, f"deadlines duplicated: {first} -> {second}"


def test_dashboard_brief(client, monkeypatch):
    """Onus drafts a plain-English brief from recent activity / actions / deadlines."""
    monkeypatch.setenv("AI_PROVIDER", "mock")
    _, token = _signup(client, "Brief Firm")
    h = {"Authorization": f"Bearer {token}"}
    res = client.post("/dashboard/brief", headers=h)
    assert res.status_code == 200, res.text
    assert res.json()["brief"]


def test_onboarding_complete_surfaces_documents(client):
    """Completing onboarding records an activity entry surfacing the prepared documents."""
    _, token = _signup(client, "Docs Ready Firm")
    h = {"Authorization": f"Bearer {token}"}
    client.post("/risk-assessment/services", json={"services": ["Property transactions"]}, headers=h)
    assert client.post("/onboarding/complete", headers=h).status_code == 200
    activity = client.get("/dashboard/summary", headers=h).json().get("recent_agent_activity", [])
    assert any("document" in a["summary"].lower() for a in activity), activity


def test_countries_rejects_out_of_range_basel(client):
    _, token = _signup(client, "Basel Firm")
    h = {"Authorization": f"Bearer {token}"}
    res = client.put(
        "/risk-assessment/countries",
        json={"countries": [{"country": "Testland", "basel_score": 15}]},
        headers=h,
    )
    assert res.status_code == 400, res.text


def test_countries_deduplicates_by_name(client):
    _, token = _signup(client, "Dedup Firm")
    h = {"Authorization": f"Bearer {token}"}
    client.put(
        "/risk-assessment/countries",
        json={
            "countries": [
                {"country": "Australia", "basel_score": 2},
                {"country": "Australia", "basel_score": 8},
            ]
        },
        headers=h,
    )
    cur = client.get("/risk-assessment/current", headers=h).json()
    assert len(cur["countries"]) == 1, cur["countries"]


def test_communication_rejects_future_date(client):
    _, token = _signup(client, "Future Comm Firm")
    h = {"Authorization": f"Bearer {token}"}
    res = client.post(
        "/risk-assessment/communications",
        json={"source_label": "AUSTRAC update", "communicated_on": "2099-01-01"},
        headers=h,
    )
    assert res.status_code == 400, res.text


def test_audit_log_export_is_csv(client):
    _, token = _signup(client, "Export Firm")
    h = {"Authorization": f"Bearer {token}"}
    res = client.get("/audit-log/export", headers=h)
    assert res.status_code == 200, res.text
    assert "text/csv" in res.headers.get("content-type", "")
    assert res.text.splitlines()[0] == "timestamp_utc,action,entity_type,entity_id,actor"


def test_data_residency_attestation_flow(client):
    """Admin can record a data-residency attestation; a member cannot (admin-gated); and
    another firm cannot see it (RLS)."""
    _, atoken = _signup(client, "Attestation Firm")
    ah = {"Authorization": f"Bearer {atoken}"}
    assert client.get("/attestation", headers=ah).json() is None
    put = client.put(
        "/attestation",
        json={"data_region": "Australia (Sydney)", "dpa_in_place": True},
        headers=ah,
    )
    assert put.status_code == 200, put.text
    assert client.get("/attestation", headers=ah).json()["data_region"] == "Australia (Sydney)"

    created = client.post(
        "/firms/users",
        json={"full_name": "M", "email": f"attm_{uuid.uuid4().hex[:8]}@test.local", "role": "member"},
        headers=ah,
    )
    temp = created.json()["temporary_password"]
    mtok = client.post(
        "/auth/login", json={"email": created.json()["user"]["email"], "password": temp}
    ).json()["access_token"]
    assert (
        client.put(
            "/attestation", json={"data_region": "x"}, headers={"Authorization": f"Bearer {mtok}"}
        ).status_code
        == 403
    )

    _, btoken = _signup(client, "Other Attestation Firm")
    assert client.get("/attestation", headers={"Authorization": f"Bearer {btoken}"}).json() is None


def test_oauth_bridge_secret_and_find_or_create(client, monkeypatch):
    """SSO bridge: disabled without the secret; with it, a new identity creates a firm +
    user and returns a working token; a wrong secret is rejected; a repeat finds the user."""
    monkeypatch.delenv("OAUTH_BRIDGE_SECRET", raising=False)
    assert (
        client.post("/auth/oauth", json={"email": "sso@x.io", "provider": "google"}).status_code
        == 401
    )
    monkeypatch.setenv("OAUTH_BRIDGE_SECRET", "test-bridge-secret")
    email = f"sso_{uuid.uuid4().hex[:8]}@x.io"
    hdr = {"X-Internal-Secret": "test-bridge-secret"}
    r = client.post(
        "/auth/oauth", json={"email": email, "full_name": "SSO User", "provider": "google"}, headers=hdr
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["email"] == email
    assert (
        client.post(
            "/auth/oauth", json={"email": email, "provider": "google"},
            headers={"X-Internal-Secret": "wrong"},
        ).status_code
        == 401
    )
    # Same identity again resolves to the same user (no duplicate), still 200.
    assert client.post("/auth/oauth", json={"email": email, "provider": "google"}, headers=hdr).status_code == 200


def test_demo_eoi_capture(client):
    """The public demo expression-of-interest endpoint stores a lead and validates email."""
    assert (
        client.post("/eoi", json={"email": "prospect@firm.com.au", "firm_name": "X"}).status_code
        == 200
    )
    assert client.post("/eoi", json={"email": "notanemail"}).status_code == 422


def test_evaluation_report_resubmit_is_audited(client):
    """Resubmitting an evaluation report replaces the prior one; the supersession must be
    recorded in the immutable audit log even though the old report is not versioned."""
    _, token = _signup(client, "Eval Audit Firm")
    h = {"Authorization": f"Bearer {token}"}
    eval_id = client.post("/evaluations", json={"is_first_evaluation": True}, headers=h).json()["id"]
    assert (
        client.post(
            f"/evaluations/{eval_id}/report", json={"summary_of_process": "first"}, headers=h
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/evaluations/{eval_id}/report", json={"summary_of_process": "second"}, headers=h
        ).status_code
        == 200
    )
    actions = [r["action"] for r in client.get("/audit-log", headers=h).json()]
    assert "evaluation.report_superseded" in actions, actions
