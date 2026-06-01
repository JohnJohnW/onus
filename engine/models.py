"""Core ORM models for Onus authentication, firm governance, and the agent feed."""
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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Firm(Base):
    """A law firm tenant. The unit of multi-tenancy / row-level security."""

    __tablename__ = "firms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    users = relationship("User", back_populates="firm")
    risk_state = relationship("FirmRiskState", back_populates="firm", uselist=False)


class User(Base):
    """A user belonging to a firm. The signup creator is an ``admin``."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="admin")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    firm = relationship("Firm", back_populates="users")


class GovernanceRole(Base):
    """A governance assignment (e.g. ``compliance_officer``) for a user at a firm."""

    __tablename__ = "governance_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FirmRiskState(Base):
    """Per-firm ML/TF risk posture. One row per firm."""

    __tablename__ = "firm_risk_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(
        UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, unique=True, index=True
    )
    # overall_risk_rating: unassessed | low | medium | high
    risk_level = Column(String, nullable=False, default="unassessed")
    status = Column(String, nullable=False, default="active")
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    firm = relationship("Firm", back_populates="risk_state")


class GovernanceApproval(Base):
    """Something requiring the principal's sign-off (e.g. program approval, EDD)."""

    __tablename__ = "governance_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    title = Column(String, nullable=False)          # what needs doing (plain English)
    rationale = Column(Text, nullable=False)         # why it matters (one sentence)
    estimate_minutes = Column(Integer, nullable=True)  # how long it will take
    action_label = Column(String, nullable=False, default="Review and approve")
    status = Column(String, nullable=False, default="pending")  # pending | approved | dismissed
    due_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ComplianceDeadline(Base):
    """A statutory or program deadline the firm must meet."""

    __tablename__ = "compliance_deadlines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    name = Column(String, nullable=False)            # plain-English deadline name
    description = Column(Text, nullable=True)         # why it matters
    estimate_minutes = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending | completed
    due_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AgentTask(Base):
    """A unit of work Onus performed on the firm's behalf (the agent feed)."""

    __tablename__ = "agent_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    summary = Column(Text, nullable=False)           # what Onus did (plain English)
    detail = Column(Text, nullable=True)
    human_action_required = Column(Boolean, nullable=False, default=False)
    human_action_outcome = Column(String, nullable=True)  # what happened, if anything
    status = Column(String, nullable=False, default="completed")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RiskAssessment(Base):
    """A firm's ML/TF risk assessment, with child category ratings."""

    __tablename__ = "risk_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="draft")  # draft | approved
    overall_rating = Column(String, nullable=False, default="unassessed")
    summary = Column(Text, nullable=False)  # plain-English explanation of the rating
    next_review_due = Column(DateTime(timezone=True), nullable=True)
    approved_by_name = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    services = relationship(
        "RiskAssessmentService", back_populates="assessment", cascade="all, delete-orphan"
    )
    client_types = relationship(
        "RiskAssessmentClientType", back_populates="assessment", cascade="all, delete-orphan"
    )
    channels = relationship(
        "RiskAssessmentChannel", back_populates="assessment", cascade="all, delete-orphan"
    )
    countries = relationship(
        "RiskAssessmentCountry", back_populates="assessment", cascade="all, delete-orphan"
    )


class RiskAssessmentService(Base):
    """Risk rating for one designated service the firm provides."""

    __tablename__ = "risk_assessment_services"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    service_name = Column(String, nullable=False)
    rating = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)

    assessment = relationship("RiskAssessment", back_populates="services")


class RiskAssessmentClientType(Base):
    """Risk rating for one client type the firm serves."""

    __tablename__ = "risk_assessment_client_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    client_type = Column(String, nullable=False)
    rating = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)

    assessment = relationship("RiskAssessment", back_populates="client_types")


class RiskAssessmentChannel(Base):
    """Risk rating for one client delivery channel."""

    __tablename__ = "risk_assessment_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    channel = Column(String, nullable=False)
    rating = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)

    assessment = relationship("RiskAssessment", back_populates="channels")


class RiskAssessmentCountry(Base):
    """A country flagged with elevated risk for the firm."""

    __tablename__ = "risk_assessment_countries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    risk_assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id"), nullable=False, index=True
    )
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    country = Column(String, nullable=False)
    rating = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)

    assessment = relationship("RiskAssessment", back_populates="countries")


class AuditLog(Base):
    """Immutable record of significant actions taken in the firm's account."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("firms.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
