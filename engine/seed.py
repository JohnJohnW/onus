"""Optional dev seed for a firm (NEW schema).

Disabled by default so it can't interfere with onboarding testing - onboarding
now generates real data. Run explicitly with --force:

    python seed.py <user-email> --force
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from database import SessionLocal
from models import (
    ComplianceDeadline,
    Firm,
    FirmRiskState,
    RiskAssessment,
    RiskAssessmentCustomerType,
    RiskAssessmentDeliveryChannel,
    RiskAssessmentService,
    User,
)


def main(email: str) -> None:
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No user found with email {email!r}")
            return
        firm_id = user.firm_id

        for model in (ComplianceDeadline, RiskAssessment):
            for row in db.scalars(select(model).where(model.firm_id == firm_id)).all():
                db.delete(row)
        db.flush()

        firm = db.get(Firm, firm_id)
        firm.firm_size = firm.firm_size or "small"
        firm.enrolment_status = "enrolled"

        ra = RiskAssessment(firm_id=firm_id, version=1, status="draft", overall_risk_rating="medium")
        ra.services = [
            RiskAssessmentService(firm_id=firm_id, designated_service_type="Company formation", inherent_risk_rating="high", explanation="Forming companies can hide who is really behind them."),
            RiskAssessmentService(firm_id=firm_id, designated_service_type="Property transactions", inherent_risk_rating="medium", explanation="Property transfers are a common laundering channel."),
        ]
        ra.customer_types = [
            RiskAssessmentCustomerType(firm_id=firm_id, customer_type="Overseas clients", inherent_risk_rating="high", explanation="Harder to verify, higher risk."),
            RiskAssessmentCustomerType(firm_id=firm_id, customer_type="Individual people", inherent_risk_rating="low", explanation="Verifiable identities, lower risk."),
        ]
        ra.delivery_channels = [
            RiskAssessmentDeliveryChannel(firm_id=firm_id, channel_type="Face to face always/usually", inherent_risk_rating="low", explanation="In-person verification is straightforward."),
        ]
        db.add(ra)

        frs = db.scalar(select(FirmRiskState).where(FirmRiskState.firm_id == firm_id))
        if frs is not None:
            frs.overall_risk_rating = "medium"

        db.add_all([
            ComplianceDeadline(firm_id=firm_id, deadline_type="enrolment", due_at=now + timedelta(days=20)),
            ComplianceDeadline(firm_id=firm_id, deadline_type="annual_report", due_at=now + timedelta(days=120)),
        ])
        db.commit()
        print(f"Seeded firm {firm_id} (user {email}).")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2 or "--force" not in sys.argv:
        print("Seeding is optional/disabled. To run: python seed.py <user-email> --force")
        raise SystemExit(0)
    main(sys.argv[1])
