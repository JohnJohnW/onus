"""ORM models for Onus — corrected to the original data-model spec."""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
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
    role = Column(String, nullable=False)  # compliance_officer | senior_manager
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    appointed_at = Column(DateTime(timezone=True), nullable=True)
    appointed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
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

    assessment = relationship("RiskAssessment", back_populates="countries")


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
