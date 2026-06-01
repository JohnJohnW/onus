"""Clients & matters - CDD execution and the before-you-act CDD gate (Act Pt 2)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from database import get_db
from models import AuditLog, CddCheck, Client, ClientParty, Matter, MonitoringAlert, User
from schemas import (
    AlertOut,
    CatalogueItem,
    CddCheckOut,
    CddRequest,
    ClientCreate,
    ClientDetailOut,
    ClientListItemOut,
    ClientsMetaOut,
    ClientUpdate,
    MatterCreate,
    MatterOut,
    PartyCreate,
    PartyOut,
)

router = APIRouter()
matters_router = APIRouter()

# Designated services a law firm provides (Act s6 Tables 5 & 6).
DESIGNATED_SERVICES: list[tuple[str, str, str]] = [
    ("T5_1", "Brokering real estate (buyer & seller)", "buyer and seller"),
    ("T5_2", "Selling/transferring real estate (not agent-brokered)", "buyer or transferee"),
    ("T6_1", "Assisting a real-estate transaction", "the person"),
    ("T6_2", "Assisting transfer of a body corporate / legal arrangement", "the person"),
    ("T6_3", "Receiving/holding/managing client money or assets", "the person"),
    ("T6_4", "Equity or debt financing", "the person"),
    ("T6_5", "Selling/transferring a shelf company", "buyer or transferee"),
    ("T6_6", "Creating or restructuring a company or trust", "the person + owners/trustees"),
    ("T6_7", "Acting as/arranging a nominee director/secretary/partner/trustee", "the nominator"),
    ("T6_8", "Acting as/arranging a nominee shareholder", "the nominator"),
    ("T6_9", "Providing a registered office / business address", "the person"),
]

CUSTOMER_TYPES: list[tuple[str, str]] = [
    ("individual", "Individual"),
    ("sole_trader", "Sole trader"),
    ("company_domestic", "Company (Australian)"),
    ("company_foreign", "Company (foreign)"),
    ("partnership", "Partnership"),
    ("partnership_limited", "Limited partnership"),
    ("trust_discretionary", "Trust - discretionary"),
    ("trust_unit", "Trust - unit"),
    ("trust_hybrid", "Trust - hybrid"),
    ("trust_bare", "Trust - bare"),
    ("trust_testamentary", "Trust - testamentary"),
    ("trust_charitable", "Trust - charitable"),
    ("incorporated_association", "Incorporated association"),
    ("unincorporated_association", "Unincorporated association"),
    ("cooperative", "Co-operative"),
    ("government_body", "Government body"),
]
_SERVICE_KEYS = {k for k, _, _ in DESIGNATED_SERVICES}


def compute_cdd_level(*, risk_rating: Optional[str], foreign_pep: bool) -> tuple[str, Optional[str]]:
    """Simplified / standard / enhanced decision (Act ss28, 31, 32)."""
    if foreign_pep:
        return "enhanced", "Foreign PEP in the customer or an associated party - enhanced CDD is mandatory (Act s32(c))."
    if risk_rating == "high":
        return "enhanced", "High ML/TF risk - enhanced CDD is mandatory (Act s32(a))."
    if risk_rating == "low":
        return "simplified", None
    return "standard", None


def _resolve_risk(provided: Optional[str], is_pep: bool, pep_kind: Optional[str]) -> str:
    if is_pep and pep_kind == "foreign":
        return "high"  # foreign PEP is always high (Act s32(c); Risk insights p.7)
    return provided or "medium"


def _party_out(p: ClientParty) -> PartyOut:
    return PartyOut(
        id=p.id,
        role=p.role,
        name=p.name,
        is_individual=p.is_individual,
        bo_basis=p.bo_basis,
        ownership_pct=float(p.ownership_pct) if p.ownership_pct is not None else None,
        is_pep=p.is_pep,
        pep_kind=p.pep_kind,
        sanctions_hit=p.sanctions_hit,
        verified=p.verified,
    )


def _matter_out(m: Matter) -> MatterOut:
    return MatterOut(
        id=m.id,
        client_id=m.client_id,
        designated_service_key=m.designated_service_key,
        description=m.description,
        status=m.status,
        cdd_gate_passed=m.cdd_gate_passed,
        cdd_gate_basis=m.cdd_gate_basis,
        risk_rating=m.risk_rating,
        opened_at=m.opened_at,
    )


def _cdd_out(c: CddCheck) -> CddCheckOut:
    return CddCheckOut(id=c.id, level=c.level, edd_reason=c.edd_reason, outcome=c.outcome, created_at=c.created_at)


def alert_out(a: MonitoringAlert) -> AlertOut:
    return AlertOut(
        id=a.id,
        client_id=a.client_id,
        matter_id=a.matter_id,
        indicator_key=a.indicator_key,
        indicator_group=a.indicator_group,
        severity=a.severity,
        narrative=a.narrative,
        status=a.status,
        smr_report_id=a.smr_report_id,
        created_at=a.created_at,
    )


def _detail(c: Client) -> ClientDetailOut:
    return ClientDetailOut(
        id=c.id,
        type=c.type,
        display_name=c.display_name,
        status=c.status,
        risk_rating=c.risk_rating,
        cdd_status=c.cdd_status,
        is_pep=c.is_pep,
        pep_kind=c.pep_kind,
        sanctions_hit=c.sanctions_hit,
        adverse_media_hit=c.adverse_media_hit,
        source_of_funds=c.source_of_funds,
        source_of_wealth=c.source_of_wealth,
        parties=[_party_out(p) for p in c.parties],
        matters=[_matter_out(m) for m in c.matters],
        cdd_checks=[_cdd_out(x) for x in sorted(c.cdd_checks, key=lambda x: x.created_at, reverse=True)],
        alerts=[alert_out(a) for a in sorted(c.alerts, key=lambda a: a.created_at, reverse=True)],
    )


def _get_client(db: Session, firm_id, client_id) -> Client:
    c = db.get(Client, client_id)
    if c is None or c.firm_id != firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    return c


@router.get("/meta", response_model=ClientsMetaOut)
def meta(current_user: User = Depends(get_current_user)) -> ClientsMetaOut:
    return ClientsMetaOut(
        customer_types=[CatalogueItem(key=k, label=lbl) for k, lbl in CUSTOMER_TYPES],
        designated_services=[CatalogueItem(key=k, label=lbl, customer=cust) for k, lbl, cust in DESIGNATED_SERVICES],
    )


@router.post("", response_model=ClientDetailOut)
def create_client(
    body: ClientCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientDetailOut:
    risk = _resolve_risk(body.risk_rating, body.is_pep, body.pep_kind)
    client = Client(
        firm_id=current_user.firm_id,
        type=body.type,
        display_name=body.display_name,
        risk_rating=risk,
        is_pep=body.is_pep,
        pep_kind=body.pep_kind,
        sanctions_hit=body.sanctions_hit,
        adverse_media_hit=body.adverse_media_hit,
    )
    db.add(client)
    db.flush()
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="client.created",
            entity_type="client",
            entity_id=client.id,
        )
    )
    db.commit()
    db.refresh(client)
    return _detail(client)


@router.get("", response_model=list[ClientListItemOut])
def list_clients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClientListItemOut]:
    rows = db.scalars(
        select(Client).where(Client.firm_id == current_user.firm_id).order_by(Client.created_at.desc())
    ).all()
    return [
        ClientListItemOut(
            id=c.id,
            type=c.type,
            display_name=c.display_name,
            risk_rating=c.risk_rating,
            cdd_status=c.cdd_status,
            is_pep=c.is_pep,
            sanctions_hit=c.sanctions_hit,
        )
        for c in rows
    ]


@router.get("/{client_id}", response_model=ClientDetailOut)
def get_client(
    client_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientDetailOut:
    return _detail(_get_client(db, current_user.firm_id, client_id))


@router.patch("/{client_id}", response_model=ClientDetailOut)
def update_client(
    client_id: str,
    body: ClientUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientDetailOut:
    c = _get_client(db, current_user.firm_id, client_id)
    if body.is_pep is not None:
        c.is_pep = body.is_pep
    if body.pep_kind is not None:
        c.pep_kind = body.pep_kind
    if body.sanctions_hit is not None:
        c.sanctions_hit = body.sanctions_hit
    if body.adverse_media_hit is not None:
        c.adverse_media_hit = body.adverse_media_hit
    if body.source_of_funds is not None:
        c.source_of_funds = body.source_of_funds
    if body.source_of_wealth is not None:
        c.source_of_wealth = body.source_of_wealth
    c.risk_rating = _resolve_risk(body.risk_rating or c.risk_rating, c.is_pep, c.pep_kind)
    db.commit()
    db.refresh(c)
    return _detail(c)


@router.post("/{client_id}/parties", response_model=ClientDetailOut)
def add_party(
    client_id: str,
    body: PartyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientDetailOut:
    c = _get_client(db, current_user.firm_id, client_id)
    db.add(
        ClientParty(
            firm_id=current_user.firm_id,
            client_id=c.id,
            role=body.role,
            name=body.name,
            is_individual=body.is_individual,
            bo_basis=body.bo_basis,
            ownership_pct=body.ownership_pct,
            is_pep=body.is_pep,
            pep_kind=body.pep_kind,
            sanctions_hit=body.sanctions_hit,
            verified=body.verified,
            verification_method=body.verification_method,
            steps_recorded=body.steps_recorded,
            details=body.details,
        )
    )
    db.commit()
    db.refresh(c)
    return _detail(c)


@router.post("/{client_id}/cdd", response_model=ClientDetailOut)
def record_cdd(
    client_id: str,
    body: CddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClientDetailOut:
    c = _get_client(db, current_user.firm_id, client_id)
    foreign_pep = (c.is_pep and c.pep_kind == "foreign") or any(
        p.is_pep and p.pep_kind == "foreign" for p in c.parties
    )
    sanctions = c.sanctions_hit or any(p.sanctions_hit for p in c.parties)
    if foreign_pep:
        c.risk_rating = "high"
    level, edd_reason = compute_cdd_level(risk_rating=c.risk_rating, foreign_pep=foreign_pep)
    if body.source_of_funds is not None:
        c.source_of_funds = body.source_of_funds
    if body.source_of_wealth is not None:
        c.source_of_wealth = body.source_of_wealth
    outcome = "fail" if sanctions else "pass"
    c.cdd_status = "blocked" if sanctions else "complete"
    now = datetime.now(timezone.utc)
    db.add(
        CddCheck(
            firm_id=current_user.firm_id,
            client_id=c.id,
            matter_id=body.matter_id,
            level=level,
            kyc_fields=body.kyc_fields,
            edd_reason=edd_reason,
            outcome=outcome,
            verified_at=now,
            verified_by_user_id=current_user.id,
        )
    )
    if body.matter_id is not None:
        m = db.get(Matter, body.matter_id)
        if m is not None and m.firm_id == current_user.firm_id:
            m.cdd_gate_passed = outcome == "pass"
            m.cdd_gate_basis = "initial_cdd" if outcome == "pass" else None
            m.risk_rating = c.risk_rating
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="cdd.completed",
            entity_type="client",
            entity_id=c.id,
            after_state={"level": level, "outcome": outcome},
        )
    )
    db.commit()
    db.refresh(c)
    return _detail(c)


@matters_router.post("", response_model=MatterOut)
def create_matter(
    body: MatterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatterOut:
    if body.designated_service_key not in _SERVICE_KEYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown designated service.")
    c = _get_client(db, current_user.firm_id, body.client_id)
    gate = c.cdd_status == "complete"
    matter = Matter(
        firm_id=current_user.firm_id,
        client_id=c.id,
        designated_service_key=body.designated_service_key,
        description=body.description,
        cdd_gate_passed=gate,
        cdd_gate_basis="initial_cdd" if gate else None,
        risk_rating=c.risk_rating,
    )
    db.add(matter)
    db.flush()
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="matter.opened",
            entity_type="matter",
            entity_id=matter.id,
        )
    )
    db.commit()
    db.refresh(matter)
    return _matter_out(matter)


@matters_router.get("/{matter_id}", response_model=MatterOut)
def get_matter(
    matter_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatterOut:
    m = db.get(Matter, matter_id)
    if m is None or m.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matter not found.")
    return _matter_out(m)
