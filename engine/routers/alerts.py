"""Suspicious-activity monitoring - indicators, alerts, and escalation to a draft SMR."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from agent_log import record_agent_task
from auth.dependencies import get_current_user
from database import get_db
from models import AuditLog, Client, Matter, MonitoringAlert, Report, ReportDecisionLog, User
from routers.clients import alert_out
from routers.reports import _compute_due, _hash
from schemas import (
    AlertCreate,
    AlertDismissRequest,
    AlertEscalateRequest,
    AlertOut,
    IndicatorOut,
    ScanResultOut,
)

router = APIRouter()

# Suspicious-activity indicators for legal professionals (Risk insights section 4).
INDICATOR_CATALOGUE: list[tuple[str, str, str, str]] = [
    ("client", "Client risk", "obscured_bo", "Ownership structure obscures the true beneficial owner"),
    ("client", "Client risk", "reluctant_kyc", "Client avoids or is evasive about KYC"),
    ("behaviour", "Client behaviour", "avoids_face_to_face", "Avoids face-to-face meetings"),
    ("behaviour", "Client behaviour", "unusual_aml_knowledge", "Unusual knowledge of AML/CTF requirements"),
    ("source_of_funds", "Source of funds/wealth", "unexplained_wealth", "Wealth inconsistent with known income / unexplained"),
    ("transactions", "Unusual transactions", "trust_account_layering", "Series of transfers layering funds through the trust account"),
    ("transactions", "Unusual transactions", "back_to_back_property", "Back-to-back property deals with rapidly rising values"),
    ("transactions", "Unusual transactions", "structuring", "Transactions structured to stay under $10,000"),
    ("structures", "Complex structures", "shell_shelf_company", "Shelf/shell/aged-company purchase with no economic reason"),
    ("structures", "Complex structures", "wholesale_entities", "Wholesale creation of companies or trusts"),
    ("structures", "Complex structures", "nominee_no_reason", "Nominee director/shareholder with no clear reason"),
    ("delivery", "Delivery channel", "unreasonable_anonymity", "Requests unreasonable anonymity, or acts via a third party with no reason"),
    ("foreign", "Foreign jurisdiction", "high_risk_jurisdiction", "Transfers to/from a high-risk or unconnected jurisdiction"),
    ("foreign", "Foreign jurisdiction", "complex_offshore", "Complicated offshore ownership with no economic rationale"),
]
_IND = {key: (group, group_label, label) for group, group_label, key, label in INDICATOR_CATALOGUE}


@router.get("/indicators", response_model=list[IndicatorOut])
def list_indicators(current_user: User = Depends(get_current_user)) -> list[IndicatorOut]:
    return [
        IndicatorOut(group=g, group_label=gl, key=k, label=lbl)
        for g, gl, k, lbl in INDICATOR_CATALOGUE
    ]


@router.get("", response_model=list[AlertOut])
def list_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertOut]:
    rows = db.scalars(
        select(MonitoringAlert)
        .where(
            MonitoringAlert.firm_id == current_user.firm_id,
            MonitoringAlert.status.in_(("open", "reviewing")),
        )
        .order_by(MonitoringAlert.created_at.desc())
    ).all()
    return [alert_out(a) for a in rows]


@router.post("", response_model=AlertOut)
def raise_alert(
    body: AlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertOut:
    if body.indicator_key not in _IND:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown indicator.")
    client = db.get(Client, body.client_id)
    if client is None or client.firm_id != current_user.firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    group, _gl, label = _IND[body.indicator_key]
    alert = MonitoringAlert(
        firm_id=current_user.firm_id,
        client_id=body.client_id,
        matter_id=body.matter_id,
        indicator_key=body.indicator_key,
        indicator_group=group,
        severity=body.severity if body.severity in ("low", "medium", "high") else "medium",
        narrative=body.narrative or label,
        status="open",
    )
    db.add(alert)
    db.flush()
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="alert.raised",
            entity_type="monitoring_alert",
            entity_id=alert.id,
        )
    )
    db.commit()
    db.refresh(alert)
    return alert_out(alert)


def _get_alert(db: Session, firm_id, alert_id) -> MonitoringAlert:
    a = db.get(MonitoringAlert, alert_id)
    if a is None or a.firm_id != firm_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    return a


@router.post("/{alert_id}/escalate", response_model=AlertOut)
def escalate_alert(
    alert_id: str,
    body: AlertEscalateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertOut:
    """Escalate an alert into a draft SMR (reasonable grounds to suspect)."""
    a = _get_alert(db, current_user.firm_id, alert_id)
    if a.status == "escalated_to_smr":
        # Already escalated; never create a second SMR for the same alert.
        return alert_out(a)
    if a.status == "dismissed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This alert was dismissed; it cannot be escalated without being re-opened.",
        )
    now = datetime.now(timezone.utc)
    due, basis = _compute_due("smr", tf=body.tf, lpp=body.lpp_claimed, trigger=now, period_end=None)
    grounds = body.reasoning or a.narrative or _IND.get(a.indicator_key, ("", "", ""))[2]
    payload = {"grounds_for_suspicion": grounds, "indicator": a.indicator_key}
    report = Report(
        firm_id=current_user.firm_id,
        type="smr",
        status="draft",
        related_client_id=a.client_id,
        related_matter_id=a.matter_id,
        related_alert_id=a.id,
        payload=payload,
        deadline_basis=basis,
        lpp_claimed=body.lpp_claimed,
        due_at=due,
        content_hash=_hash(payload),
    )
    db.add(report)
    db.flush()
    a.status = "escalated_to_smr"
    a.smr_report_id = report.id
    db.add(
        ReportDecisionLog(
            firm_id=current_user.firm_id,
            report_id=report.id,
            client_id=a.client_id,
            matter_id=a.matter_id,
            reasonable_grounds=True,
            reasoning=grounds,
            decided_by_user_id=current_user.id,
        )
    )
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="alert.escalated_to_smr",
            entity_type="monitoring_alert",
            entity_id=a.id,
        )
    )
    db.commit()
    db.refresh(a)
    return alert_out(a)


@router.post("/{alert_id}/dismiss", response_model=AlertOut)
def dismiss_alert(
    alert_id: str,
    body: AlertDismissRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertOut:
    a = _get_alert(db, current_user.firm_id, alert_id)
    if a.status == "escalated_to_smr":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This alert was escalated to an SMR and cannot be dismissed.",
        )
    a.status = "dismissed"
    db.add(
        ReportDecisionLog(
            firm_id=current_user.firm_id,
            client_id=a.client_id,
            matter_id=a.matter_id,
            reasonable_grounds=False,
            reasoning=body.reasoning or "No reasonable grounds to suspect.",
            decided_by_user_id=current_user.id,
        )
    )
    db.add(
        AuditLog(
            firm_id=current_user.firm_id,
            user_id=current_user.id,
            action="alert.dismissed",
            entity_type="monitoring_alert",
            entity_id=a.id,
        )
    )
    db.commit()
    db.refresh(a)
    return alert_out(a)


# Automated monitoring rules. Each evaluates a real compliance risk condition over the
# firm's own client/matter records (Onus has no transaction feed, so this is
# risk-condition monitoring, not transaction monitoring). De-duplicated on open status.
def _scan_rules(client: Client, has_matter: bool):
    rules = []
    if client.sanctions_hit and has_matter:
        rules.append((
            "sanctions_flagged_active", "high",
            f"{client.display_name}: a sanctions-flagged client has an open matter. "
            "You must not provide a designated service (Act s28).",
        ))
    if client.is_pep and client.pep_kind == "foreign" and client.cdd_status != "complete":
        rules.append((
            "foreign_pep_cdd_incomplete", "high",
            f"{client.display_name}: foreign PEP without completed enhanced CDD (Rules s5-5).",
        ))
    if client.risk_rating == "high" and client.cdd_status != "complete":
        rules.append((
            "high_risk_cdd_incomplete", "medium",
            f"{client.display_name}: high ML/TF-risk client without completed CDD.",
        ))
    return rules


@router.post("/scan", response_model=ScanResultOut)
def scan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanResultOut:
    """Run automated monitoring: evaluate compliance risk conditions across the firm's
    clients and raise an alert for each new finding (Onus doing the watching)."""
    firm_id = current_user.firm_id
    clients = db.scalars(select(Client).where(Client.firm_id == firm_id)).all()
    raised: list[MonitoringAlert] = []
    for client in clients:
        matter = db.scalar(
            select(Matter).where(Matter.firm_id == firm_id, Matter.client_id == client.id)
        )
        for key, severity, narrative in _scan_rules(client, matter is not None):
            existing = db.scalar(
                select(MonitoringAlert).where(
                    MonitoringAlert.firm_id == firm_id,
                    MonitoringAlert.client_id == client.id,
                    MonitoringAlert.indicator_key == key,
                    MonitoringAlert.status == "open",
                )
            )
            if existing is not None:
                continue  # don't re-raise the same open finding
            alert = MonitoringAlert(
                firm_id=firm_id,
                client_id=client.id,
                matter_id=matter.id if (key == "sanctions_flagged_active" and matter) else None,
                indicator_key=key,
                indicator_group="automated_monitoring",
                severity=severity,
                narrative=narrative,
                status="open",
            )
            db.add(alert)
            db.flush()
            raised.append(alert)
    if raised:
        record_agent_task(
            db,
            firm_id,
            task_type="monitoring_scan",
            summary=f"Monitoring scan raised {len(raised)} new alert{'' if len(raised) == 1 else 's'}",
            human_action_required=True,
            human_action_type="review_alerts",
        )
    db.commit()
    return ScanResultOut(raised=len(raised), alerts=[alert_out(a) for a in raised])
