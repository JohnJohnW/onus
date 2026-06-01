"""Dev seed: populate a firm with realistic sample dashboard + risk data.

Usage (inside the engine container):
    python seed.py <user-email>

Idempotent: clears this firm's existing agent_tasks / approvals / deadlines /
risk assessment first.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from database import SessionLocal
from models import (
    AgentTask,
    ComplianceDeadline,
    FirmRiskState,
    GovernanceApproval,
    RiskAssessment,
    RiskAssessmentChannel,
    RiskAssessmentClientType,
    RiskAssessmentCountry,
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

        risk = db.scalar(select(FirmRiskState).where(FirmRiskState.firm_id == firm_id))
        if risk is not None:
            risk.risk_level = "medium"

        # Clear prior seed data for this firm (idempotent re-seed).
        for model in (AgentTask, GovernanceApproval, ComplianceDeadline, RiskAssessment):
            for row in db.scalars(select(model).where(model.firm_id == firm_id)).all():
                db.delete(row)
        db.flush()

        db.add_all(
            [
                AgentTask(
                    firm_id=firm_id,
                    summary="Screened 4 new clients against sanctions and PEP watchlists. No matches found.",
                    created_at=now - timedelta(minutes=35),
                    human_action_required=False,
                ),
                AgentTask(
                    firm_id=firm_id,
                    summary="Flagged a high-value international transfer on the Meridian Holdings matter for enhanced due diligence.",
                    created_at=now - timedelta(hours=2),
                    human_action_required=True,
                    human_action_outcome="Awaiting your review",
                    status="awaiting_action",
                ),
                AgentTask(
                    firm_id=firm_id,
                    summary="Generated this quarter's AML/CTF compliance report and filed it to your records.",
                    created_at=now - timedelta(hours=6),
                    human_action_required=False,
                    human_action_outcome="No action needed",
                ),
                AgentTask(
                    firm_id=firm_id,
                    summary="Identified a politically exposed person during new client intake and opened an EDD review.",
                    created_at=now - timedelta(days=1, hours=3),
                    human_action_required=True,
                    human_action_outcome="Escalated to you",
                    status="awaiting_action",
                ),
                AgentTask(
                    firm_id=firm_id,
                    summary="Refreshed the firm-wide ML/TF risk assessment after onboarding two corporate clients.",
                    created_at=now - timedelta(days=2),
                    human_action_required=False,
                ),
            ]
        )

        db.add_all(
            [
                GovernanceApproval(
                    firm_id=firm_id,
                    title="Approve the updated AML/CTF program",
                    rationale="Your program must be reviewed and approved by the principal to stay compliant under the AML/CTF Act.",
                    estimate_minutes=15,
                    action_label="Review and approve",
                    due_at=now + timedelta(days=5),
                ),
                GovernanceApproval(
                    firm_id=firm_id,
                    title="Sign off enhanced due diligence on Meridian Holdings",
                    rationale="A high-risk client cannot proceed until the principal approves the enhanced due diligence findings.",
                    estimate_minutes=10,
                    action_label="Review and approve",
                    due_at=now + timedelta(days=2),
                ),
            ]
        )

        db.add_all(
            [
                ComplianceDeadline(
                    firm_id=firm_id,
                    name="Lodge AUSTRAC annual compliance report",
                    description="The annual compliance report is due to AUSTRAC and must be lodged by the principal.",
                    estimate_minutes=30,
                    due_at=now + timedelta(days=9),
                ),
                ComplianceDeadline(
                    firm_id=firm_id,
                    name="Independent review of the AML/CTF program",
                    due_at=now + timedelta(days=24),
                ),
                ComplianceDeadline(
                    firm_id=firm_id,
                    name="Refresh customer due diligence for ongoing clients",
                    due_at=now + timedelta(days=46),
                ),
            ]
        )

        assessment = RiskAssessment(
            firm_id=firm_id,
            status="draft",
            overall_rating="medium",
            summary=(
                "Your firm's overall money-laundering and terrorism-financing risk is medium. "
                "You take on some higher-risk work — like forming companies and trusts and holding "
                "client money — so Onus applies extra checks on those matters. Your mostly local "
                "client base and in-person onboarding keep your overall exposure manageable, as "
                "long as those enhanced checks stay in place."
            ),
            next_review_due=now + timedelta(days=365),
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
        assessment.services = [
            RiskAssessmentService(
                firm_id=firm_id,
                service_name="Conveyancing and real-estate transfers",
                rating="medium",
                explanation="Property transactions are a common way to move illicit funds, so these matters get closer scrutiny.",
            ),
            RiskAssessmentService(
                firm_id=firm_id,
                service_name="Forming companies and trusts",
                rating="high",
                explanation="Company and trust structures can hide who really owns assets, which makes this higher risk.",
            ),
            RiskAssessmentService(
                firm_id=firm_id,
                service_name="Holding or managing client money",
                rating="high",
                explanation="Handling client funds directly is one of the highest-risk activities a firm can undertake.",
            ),
            RiskAssessmentService(
                firm_id=firm_id,
                service_name="Acting as a registered office or agent",
                rating="low",
                explanation="Providing a registered address on its own carries little money-laundering risk.",
            ),
        ]
        assessment.client_types = [
            RiskAssessmentClientType(
                firm_id=firm_id,
                client_type="Established local individuals",
                rating="low",
                explanation="Long-standing local clients with clear identities are lower risk.",
            ),
            RiskAssessmentClientType(
                firm_id=firm_id,
                client_type="Domestic companies and trusts",
                rating="medium",
                explanation="Corporate clients need extra checks to confirm who ultimately controls them.",
            ),
            RiskAssessmentClientType(
                firm_id=firm_id,
                client_type="Overseas or non-resident clients",
                rating="high",
                explanation="Clients based overseas are harder to verify and carry higher risk.",
            ),
        ]
        assessment.channels = [
            RiskAssessmentChannel(
                firm_id=firm_id,
                channel="In-person onboarding",
                rating="low",
                explanation="Meeting clients face-to-face makes it easier to confirm who they are.",
            ),
            RiskAssessmentChannel(
                firm_id=firm_id,
                channel="Fully remote onboarding",
                rating="medium",
                explanation="Onboarding clients you never meet in person needs stronger identity checks.",
            ),
        ]
        assessment.countries = [
            RiskAssessmentCountry(
                firm_id=firm_id,
                country="British Virgin Islands",
                rating="high",
                explanation="A jurisdiction with limited transparency over who owns companies.",
            ),
            RiskAssessmentCountry(
                firm_id=firm_id,
                country="United Arab Emirates",
                rating="medium",
                explanation="Flagged for heightened monitoring on certain cross-border transactions.",
            ),
        ]
        db.add(assessment)

        db.commit()
        print(f"Seeded firm {firm_id} (user {email}) with sample dashboard + risk data.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python seed.py <user-email>")
        raise SystemExit(1)
    main(sys.argv[1])
