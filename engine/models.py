"""ORM models for Onus — corrected to the original data-model spec."""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from database import Base


class Firm(Base):
    __tablename__ = "firms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    abn = Column(String, nullable=True)
    firm_size = Column(String, nullable=True)
    practice_areas = Column(JSONB, nullable=True)
    onboarding_completed = Column(Boolean, nullable=False, server_default=text("false"))
    onboarding_step = Column(Integer, nullable=False, server_default=text("0"))
    austrac_enrolment_number = Column(String, nullable=True)
    enrolment_status = Column(String, nullable=False, server_default="not_enrolled")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="firm", foreign_keys="User.firm_id")
    risk_state = relationship("FirmRiskState", back_populates="firm", uselist=False)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, server_default="admin")
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    firm = relationship("Firm", back_populates="users", foreign_keys=[firm_id])


class GovernanceRole(Base):
    __tablename__ = "governance_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    # governing_body | senior_manager | compliance_officer | independent_evaluator
    role = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    appointed_at = Column(DateTime(timezone=True), nullable=True)
    appointed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    # Eligibility (compliance officer — Act s26J; Rules s5-14)
    management_level = Column(Boolean, nullable=False, server_default=text("false"))
    is_australian_resident = Column(Boolean, nullable=False, server_default=text("false"))
    fit_and_proper_considered = Column(Boolean, nullable=False, server_default=text("false"))
    qualifies_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FirmRiskState(Base):
    __tablename__ = "firm_risk_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(
        UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, unique=True, index=True
    )
    overall_risk_rating = Column(String, nullable=False, server_default="unassessed")
    risk_factors = Column(JSONB, nullable=True)
    status = Column(String, nullable=False, server_default="active")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    firm = relationship("Firm", back_populates="risk_state")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, server_default=text("1"))
    status = Column(String, nullable=False, server_default="draft")  # draft | approved
    overall_risk_rating = Column(String, nullable=False, server_default="unassessed")
    summary = Column(Text, nullable=True)
    # impact_only (low-complexity firms) | likelihood_x_impact (medium complexity) — Step 2 p.26
    methodology = Column(String, nullable=False, server_default="impact_only")
    complexity_tier = Column(String, nullable=False, server_default="low")  # low | medium | high
    pf_assessed = Column(Boolean, nullable=False, server_default=text("false"))  # Act s26C(1)
    pf_risk_rating = Column(String, nullable=True)  # low | medium | high
    pf_rationale = Column(Text, nullable=True)
    next_review_due_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_name = Column(String, nullable=True)
    approved_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    services = relationship(
        "RiskAssessmentService", back_populates="assessment", cascade="all, delete-orphan"
    )
    customer_types = relationship(
        "RiskAssessmentCustomerType", back_populates="assessment", cascade="all, delete-orphan"
    )
    delivery_channels = relationship(
        "RiskAssessmentDeliveryChannel", back_populates="assessment", cascade="all, delete-orphan"
    )
    countries = relationship(
        "RiskAssessmentCountry", back_populates="assessment", cascade="all, delete-orphan"
    )


class RiskAssessmentService(Base):
    __tablename__ = "risk_assessment_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    designated_service_type = Column(String, nullable=False)
    inherent_risk_rating = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    likelihood = Column(String, nullable=True)  # not_likely | likely | very_likely
    impact = Column(String, nullable=True)  # low | medium | high
    data_source = Column(Text, nullable=True)  # rationale source (Step 2 p.30)
    is_planned = Column(Boolean, nullable=False, server_default=text("false"))

    assessment = relationship("RiskAssessment", back_populates="services")


class RiskAssessmentCustomerType(Base):
    __tablename__ = "risk_assessment_customer_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    customer_type = Column(String, nullable=False)
    inherent_risk_rating = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    likelihood = Column(String, nullable=True)
    impact = Column(String, nullable=True)
    data_source = Column(Text, nullable=True)
    is_planned = Column(Boolean, nullable=False, server_default=text("false"))

    assessment = relationship("RiskAssessment", back_populates="customer_types")


class RiskAssessmentDeliveryChannel(Base):
    __tablename__ = "risk_assessment_delivery_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    channel_type = Column(String, nullable=False)
    inherent_risk_rating = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    likelihood = Column(String, nullable=True)
    impact = Column(String, nullable=True)
    data_source = Column(Text, nullable=True)
    is_planned = Column(Boolean, nullable=False, server_default=text("false"))

    assessment = relationship("RiskAssessment", back_populates="delivery_channels")


class RiskAssessmentCountry(Base):
    __tablename__ = "risk_assessment_countries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    country = Column(String, nullable=False)
    inherent_risk_rating = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    # Country-risk overrides — AUSTRAC "High-risk countries, regions and groups"
    basel_score = Column(Numeric(4, 2), nullable=True)  # Basel AML Index (Step 2 banding)
    fatf_listed = Column(Boolean, nullable=False, server_default=text("false"))
    sanctions_listed = Column(Boolean, nullable=False, server_default=text("false"))
    prescribed_foreign_country = Column(Boolean, nullable=False, server_default=text("false"))
    tax_haven = Column(Boolean, nullable=False, server_default=text("false"))
    terrorism_support = Column(Boolean, nullable=False, server_default=text("false"))

    assessment = relationship("RiskAssessment", back_populates="countries")


class AustracCommunication(Base):
    """The AUSTRAC communications register (Step 2 pp.22-23; Act s26C(3)(e))."""

    __tablename__ = "austrac_communications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    source_label = Column(String, nullable=False)  # e.g. "ML NRA 2024", "AUSTRAC InBrief"
    communicated_on = Column(Date, nullable=True)
    relevance_note = Column(Text, nullable=True)  # why is it relevant?
    change_made = Column(Text, nullable=True)  # what changed and how?
    considered_on = Column(Date, nullable=True)
    reviewer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    review_trigger_id = Column(UUID(as_uuid=True), ForeignKey("review_triggers.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class GovernanceApproval(Base):
    __tablename__ = "governance_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    rationale = Column(Text, nullable=False)
    estimate_minutes = Column(Integer, nullable=True)
    action_label = Column(String, nullable=False, server_default="Review and approve")
    status = Column(String, nullable=False, server_default="pending")
    due_at = Column(DateTime(timezone=True), nullable=True)
    # What is being approved (Act s26P; Rules s5-5)
    subject_type = Column(String, nullable=True)  # program | policy | risk_assessment | pep_relationship | ...
    subject_id = Column(UUID(as_uuid=True), nullable=True)
    escalation_reason = Column(Text, nullable=True)
    # Who decided — name/role/date (s26P; Senior-manager guidance p.8)
    approved_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approver_name = Column(String, nullable=True)
    approver_role = Column(String, nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision = Column(String, nullable=True)  # approved | not_approved
    decision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AmlProgram(Base):
    """The AML/CTF program container = risk assessment + policies (Act Pt 1A)."""

    __tablename__ = "aml_programs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(
        UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, unique=True, index=True
    )
    status = Column(String, nullable=False, server_default="draft")  # draft | approved | under_review
    version = Column(Integer, nullable=False, server_default=text("1"))
    documented_at = Column(DateTime(timezone=True), nullable=True)
    risk_assessment_id = Column(UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=True)
    approved_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_by_name = Column(String, nullable=True)
    approved_by_role = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    next_review_due_at = Column(DateTime(timezone=True), nullable=True)  # approved_at + 3 years
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    policies = relationship("Policy", back_populates="program", cascade="all, delete-orphan")


class Policy(Base):
    """An AML/CTF policy (Act s26F; Rules Pt 5). One per obligation area."""

    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    program_id = Column(UUID(as_uuid=True), ForeignKey("aml_programs.id"), nullable=False, index=True)
    area_key = Column(String, nullable=False)  # matches the policy catalogue
    obligation_key = Column(String, nullable=True)  # obligation it satisfies (coverage)
    act_reference = Column(String, nullable=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    status = Column(String, nullable=False, server_default="draft")  # draft | approved
    version = Column(Integer, nullable=False, server_default=text("1"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    program = relationship("AmlProgram", back_populates="policies")


class ProgramChangeLog(Base):
    """A logged change to the program — review/update lifecycle (Act s26D; Step 4)."""

    __tablename__ = "program_change_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    entity_type = Column(String, nullable=False)  # risk_assessment | policy | program
    change_summary = Column(Text, nullable=False)
    # significant_change | austrac_communication | three_year_review | evaluation_adverse_finding | other
    trigger = Column(String, nullable=False, server_default="other")
    is_material = Column(Boolean, nullable=False, server_default=text("false"))
    documented = Column(Boolean, nullable=False, server_default=text("true"))
    due_at = Column(DateTime(timezone=True), nullable=True)  # changed_at + 14 days (Rules s5-15)
    approval_id = Column(UUID(as_uuid=True), ForeignKey("governance_approvals.id"), nullable=True)
    governing_body_notified_at = Column(DateTime(timezone=True), nullable=True)
    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ComplianceDeadline(Base):
    __tablename__ = "compliance_deadlines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    deadline_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False, server_default="pending")
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ReviewTrigger(Base):
    __tablename__ = "review_triggers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    trigger_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    review_required_by = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=False, server_default="pending")
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    before_state = Column(JSONB, nullable=True)
    after_state = Column(JSONB, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    agent_type = Column(String, nullable=True)
    task_type = Column(String, nullable=True)
    status = Column(String, nullable=False, server_default="pending")
    input_state = Column(JSONB, nullable=True)
    output_state = Column(JSONB, nullable=True)
    human_action_required = Column(Boolean, nullable=False, server_default=text("false"))
    human_action_type = Column(String, nullable=True)
    human_action_taken_at = Column(DateTime(timezone=True), nullable=True)
    human_action_taken_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Client(Base):
    """A customer of the firm (Act Pt 2 — customer due diligence)."""

    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # individual | company_domestic | trust_* | ... (Rules Pt 6)
    display_name = Column(String, nullable=False)
    status = Column(String, nullable=False, server_default="active")
    risk_rating = Column(String, nullable=True)  # low | medium | high
    cdd_status = Column(String, nullable=False, server_default="not_started")  # not_started|in_progress|complete|blocked
    is_pep = Column(Boolean, nullable=False, server_default=text("false"))
    pep_kind = Column(String, nullable=True)  # foreign | domestic | intl_org
    sanctions_hit = Column(Boolean, nullable=False, server_default=text("false"))
    adverse_media_hit = Column(Boolean, nullable=False, server_default=text("false"))
    source_of_funds = Column(Text, nullable=True)
    source_of_wealth = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    parties = relationship("ClientParty", back_populates="client", cascade="all, delete-orphan")
    matters = relationship("Matter", back_populates="client", cascade="all, delete-orphan")
    cdd_checks = relationship("CddCheck", back_populates="client", cascade="all, delete-orphan")
    alerts = relationship("MonitoringAlert", cascade="all, delete-orphan")


class ClientParty(Base):
    """Beneficial owner / controller / agent / trust role (Act s28(2)(b)-(d))."""

    __tablename__ = "client_parties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # beneficial_owner | controller | agent | trustee | ...
    name = Column(String, nullable=False)
    details = Column(JSONB, nullable=True)
    bo_basis = Column(String, nullable=True)  # ownership_25pct | control | both | none | ceo_fallback | ...
    ownership_pct = Column(Numeric(5, 2), nullable=True)
    is_individual = Column(Boolean, nullable=False, server_default=text("true"))
    is_pep = Column(Boolean, nullable=False, server_default=text("false"))
    pep_kind = Column(String, nullable=True)
    sanctions_hit = Column(Boolean, nullable=False, server_default=text("false"))
    verified = Column(Boolean, nullable=False, server_default=text("false"))
    verification_method = Column(String, nullable=True)
    steps_recorded = Column(Text, nullable=True)  # s6-8(1)(c) all-reasonable-steps log
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    client = relationship("Client", back_populates="parties")


class Matter(Base):
    """A matter — a designated service provided to a client (Act s6 Tables 5/6)."""

    __tablename__ = "matters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    designated_service_key = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, server_default="open")
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    cdd_gate_passed = Column(Boolean, nullable=False, server_default=text("false"))
    cdd_gate_basis = Column(String, nullable=True)  # initial_cdd | delayed_s29 | acip_transitional
    risk_rating = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    client = relationship("Client", back_populates="matters")


class CddCheck(Base):
    """A recorded CDD assessment (Act ss28-32; Rules Pt 6)."""

    __tablename__ = "cdd_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    matter_id = Column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)
    level = Column(String, nullable=False)  # simplified | standard | enhanced
    kyc_fields = Column(JSONB, nullable=True)
    edd_reason = Column(Text, nullable=True)
    outcome = Column(String, nullable=False, server_default="pending")  # pass | fail | pending
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    client = relationship("Client", back_populates="cdd_checks")


class Report(Base):
    """An AUSTRAC report — SMR / TTR / IFTI / annual compliance (Act Pt 3)."""

    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # smr | ttr | ifti | annual_compliance | cross_border_bni | enrolment
    status = Column(String, nullable=False, server_default="draft")  # draft | ready | lodged | not_required
    related_client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    related_matter_id = Column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)
    related_alert_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_alerts.id"), nullable=True)
    payload = Column(JSONB, nullable=True)
    deadline_basis = Column(String, nullable=True)
    lpp_claimed = Column(Boolean, nullable=False, server_default=text("false"))
    lpp_form_ref = Column(String, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    lodged_at = Column(DateTime(timezone=True), nullable=True)
    lodged_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reference_number = Column(String, nullable=True)  # AUSTRAC receipt
    content_hash = Column(String, nullable=True)  # integrity (Rules s5-11)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ReportDecisionLog(Base):
    """The "reasonable grounds to suspect" reasoning behind reporting (Rules s5-12)."""

    __tablename__ = "report_decision_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    matter_id = Column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)
    reasonable_grounds = Column(Boolean, nullable=False, server_default=text("false"))
    reasoning = Column(Text, nullable=True)
    decided_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    decided_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Record(Base):
    """Retention register — 7 years from one of four start events (Act ss107-116)."""

    __tablename__ = "records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    # from_creation (s107) | from_receipt (s108) | from_relationship_end (s111/114) | from_no_longer_relevant (s116)
    retention_basis = Column(String, nullable=False, server_default="from_creation")
    basis_date = Column(Date, nullable=True)
    retention_until = Column(Date, nullable=True)
    storage_ref = Column(String, nullable=True)
    immutable = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IndependentEvaluation(Base):
    """Periodic independent evaluation of the AML/CTF program (Act s26F(4)(f); Step 5)."""

    __tablename__ = "independent_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    status = Column(String, nullable=False, server_default="scheduled")  # scheduled|in_progress|report_received|remediating|closed
    frequency_months = Column(Integer, nullable=True)
    frequency_rationale = Column(Text, nullable=True)
    is_first_evaluation = Column(Boolean, nullable=False, server_default=text("false"))
    statutory_deadline = Column(Date, nullable=True)  # AAN-staggered (Transitional Rules s17)
    scheduled_for = Column(Date, nullable=True)
    report_received_at = Column(DateTime(timezone=True), nullable=True)
    distributed_to_governing_body_at = Column(DateTime(timezone=True), nullable=True)
    distributed_to_senior_manager_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    evaluator = relationship(
        "Evaluator", back_populates="evaluation", uselist=False, cascade="all, delete-orphan"
    )
    report = relationship(
        "EvaluationReport", back_populates="evaluation", uselist=False, cascade="all, delete-orphan"
    )
    findings = relationship(
        "EvaluationFinding", back_populates="evaluation", cascade="all, delete-orphan"
    )


class Evaluator(Base):
    """The evaluator — must be independent of the compliance function (Step 5 p.6)."""

    __tablename__ = "evaluators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    evaluation_id = Column(
        UUID(as_uuid=True), ForeignKey("independent_evaluations.id"), nullable=False, index=True
    )
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False, server_default="external")  # internal | external
    independence_confirmed = Column(Boolean, nullable=False, server_default=text("false"))
    is_compliance_officer = Column(Boolean, nullable=False, server_default=text("false"))
    independence_checklist = Column(JSONB, nullable=True)
    suitability_scorecard = Column(JSONB, nullable=True)
    selection_rationale = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluation = relationship("IndependentEvaluation", back_populates="evaluator")


class EvaluationReport(Base):
    """The written evaluation report (Step 5 p.10)."""

    __tablename__ = "evaluation_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(
        UUID(as_uuid=True), ForeignKey("independent_evaluations.id"), nullable=False, index=True
    )
    summary_of_process = Column(Text, nullable=True)
    aspects_reviewed = Column(Text, nullable=True)
    method = Column(Text, nullable=True)
    findings_risk_assessment = Column(Text, nullable=True)
    findings_policy_design = Column(Text, nullable=True)
    findings_compliance = Column(Text, nullable=True)
    items_tested = Column(Text, nullable=True)
    files_sampled = Column(Text, nullable=True)
    sampling_method = Column(Text, nullable=True)
    document_ref = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluation = relationship("IndependentEvaluation", back_populates="report")


class EvaluationFinding(Base):
    """A finding from the evaluation; adverse findings trigger review (Step 5 pp.12-14)."""

    __tablename__ = "evaluation_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    evaluation_id = Column(
        UUID(as_uuid=True), ForeignKey("independent_evaluations.id"), nullable=False, index=True
    )
    area = Column(String, nullable=False)  # risk_assessment | policy | compliance
    is_adverse = Column(Boolean, nullable=False, server_default=text("false"))
    description = Column(Text, nullable=False)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    remediation_action = Column(Text, nullable=True)
    status = Column(String, nullable=False, server_default="open")  # open|in_progress|done|wont_fix
    wont_fix_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluation = relationship("IndependentEvaluation", back_populates="findings")


class MonitoringAlert(Base):
    """A suspicious-activity indicator raised on a client/matter (Risk insights §4)."""

    __tablename__ = "monitoring_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    matter_id = Column(UUID(as_uuid=True), ForeignKey("matters.id"), nullable=True)
    indicator_key = Column(String, nullable=False)
    indicator_group = Column(String, nullable=False)
    severity = Column(String, nullable=False, server_default="medium")  # low | medium | high
    narrative = Column(Text, nullable=True)
    status = Column(String, nullable=False, server_default="open")  # open|reviewing|escalated_to_smr|dismissed
    smr_report_id = Column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
