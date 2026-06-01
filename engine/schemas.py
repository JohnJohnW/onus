"""Pydantic request/response schemas for the Onus API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ----- Auth -----

class SignupRequest(BaseModel):
    firm_name: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    password: str = Field(min_length=12, description="Minimum 12 characters.")


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    role: str
    firm_id: uuid.UUID


class FirmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    abn: Optional[str] = None
    firm_size: Optional[str] = None
    practice_areas: Optional[List[str]] = None
    onboarding_completed: bool
    onboarding_step: int
    austrac_enrolment_number: Optional[str] = None
    enrolment_status: str


class UserWithFirm(UserOut):
    firm: FirmOut


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ----- Onboarding requests -----

class FirmUpdate(BaseModel):
    name: Optional[str] = None
    abn: Optional[str] = None
    firm_size: Optional[str] = None
    practice_areas: Optional[List[str]] = None
    austrac_enrolment_number: Optional[str] = None
    enrolment_status: Optional[str] = None
    onboarding_step: Optional[int] = None


class GovernanceRolesRequest(BaseModel):
    compliance_officer_user_id: Optional[uuid.UUID] = None
    senior_manager_user_id: Optional[uuid.UUID] = None
    onboarding_step: Optional[int] = None


class ServicesRequest(BaseModel):
    services: List[str] = []
    onboarding_step: Optional[int] = None


class CustomerTypesRequest(BaseModel):
    customer_types: List[str] = []
    onboarding_step: Optional[int] = None


class DeliveryChannelsRequest(BaseModel):
    channels: List[str] = []
    onboarding_step: Optional[int] = None


# ----- Dashboard -----

class PendingActionOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    why: str
    estimate_label: Optional[str] = None
    action_label: str
    href: Optional[str] = None
    due_at: Optional[datetime] = None
    days_remaining: Optional[int] = None


class AgentActivityOut(BaseModel):
    id: uuid.UUID
    summary: str
    created_at: datetime
    human_action_required: bool
    human_action_outcome: Optional[str] = None


class UpcomingDeadlineOut(BaseModel):
    id: uuid.UUID
    name: str
    due_at: datetime
    days_remaining: int


class DashboardSummary(BaseModel):
    firm_risk_rating: str
    pending_actions: List[PendingActionOut]
    recent_agent_activity: List[AgentActivityOut]
    upcoming_deadlines: List[UpcomingDeadlineOut]


# ----- Risk assessment -----

class RiskItemOut(BaseModel):
    id: uuid.UUID
    name: str
    rating: str
    explanation: str
    likelihood: Optional[str] = None
    impact: Optional[str] = None
    data_source: Optional[str] = None
    is_planned: bool = False


class CountryItemOut(RiskItemOut):
    basel_score: Optional[float] = None
    fatf_listed: bool = False
    sanctions_listed: bool = False
    prescribed_foreign_country: bool = False
    tax_haven: bool = False
    terrorism_support: bool = False


class RiskAssessmentOut(BaseModel):
    id: uuid.UUID
    status: str
    overall_rating: str
    summary: Optional[str] = None
    methodology: str = "impact_only"
    complexity_tier: str = "low"
    pf_assessed: bool = False
    pf_risk_rating: Optional[str] = None
    pf_rationale: Optional[str] = None
    next_review_due: Optional[datetime] = None
    updated_at: datetime
    created_at: datetime
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    senior_manager_name: str
    services: List[RiskItemOut]
    client_types: List[RiskItemOut]
    channels: List[RiskItemOut]
    countries: List[CountryItemOut]


# ----- Risk assessment: enhancement requests -----

class CountryItemIn(BaseModel):
    country: str
    basel_score: Optional[float] = None
    fatf_listed: bool = False
    sanctions_listed: bool = False
    prescribed_foreign_country: bool = False
    tax_haven: bool = False
    terrorism_support: bool = False


class CountriesRequest(BaseModel):
    countries: List[CountryItemIn] = []
    onboarding_step: Optional[int] = None


class PfRequest(BaseModel):
    """Four-criterion proliferation-financing screen (Step 2 pp.24-25)."""
    australia_only_operations: bool
    no_high_risk_jurisdiction_customers: bool
    no_value_or_dual_use_goods_movement: bool
    no_pf_relevant_service: bool


class MethodologyRequest(BaseModel):
    methodology: str  # impact_only | likelihood_x_impact
    complexity_tier: Optional[str] = None  # low | medium | high


class CommunicationIn(BaseModel):
    source_label: str
    communicated_on: Optional[str] = None  # ISO date
    relevance_note: Optional[str] = None
    change_made: Optional[str] = None


class CommunicationOut(BaseModel):
    id: uuid.UUID
    source_label: str
    communicated_on: Optional[str] = None
    relevance_note: Optional[str] = None
    change_made: Optional[str] = None
    considered_on: Optional[str] = None
    reviewer: Optional[str] = None
    created_at: datetime


# ----- Settings & audit -----

class GovernanceRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    user_id: Optional[uuid.UUID] = None
    is_active: bool
    appointed_at: Optional[datetime] = None


class FirmSettingsOut(BaseModel):
    firm: FirmOut
    users: List[UserOut]
    governance_roles: List[GovernanceRoleOut]


class AuditLogOut(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: Optional[str] = None
    actor: Optional[str] = None
    created_at: datetime


# ----- Compliance program -----

class PolicyOut(BaseModel):
    id: uuid.UUID
    area_key: str
    title: str
    body: Optional[str] = None
    status: str
    obligation_key: Optional[str] = None
    act_reference: Optional[str] = None
    documented: bool


class PolicyUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None


class ProgramOut(BaseModel):
    id: uuid.UUID
    status: str
    version: int
    documented_at: Optional[datetime] = None
    approved_by_name: Optional[str] = None
    approved_by_role: Optional[str] = None
    approved_at: Optional[datetime] = None
    next_review_due: Optional[datetime] = None
    risk_assessment_status: Optional[str] = None
    documented_count: int
    total_count: int
    policies: List[PolicyOut]
    roles: List[GovernanceRoleOut]


class ProgramApproveRequest(BaseModel):
    decision_reason: Optional[str] = None


# ----- Clients & matters -----

class ClientCreate(BaseModel):
    type: str
    display_name: str
    risk_rating: Optional[str] = None
    is_pep: bool = False
    pep_kind: Optional[str] = None
    sanctions_hit: bool = False
    adverse_media_hit: bool = False


class ClientUpdate(BaseModel):
    risk_rating: Optional[str] = None
    is_pep: Optional[bool] = None
    pep_kind: Optional[str] = None
    sanctions_hit: Optional[bool] = None
    adverse_media_hit: Optional[bool] = None
    source_of_funds: Optional[str] = None
    source_of_wealth: Optional[str] = None


class PartyCreate(BaseModel):
    role: str
    name: str
    is_individual: bool = True
    bo_basis: Optional[str] = None
    ownership_pct: Optional[float] = None
    is_pep: bool = False
    pep_kind: Optional[str] = None
    sanctions_hit: bool = False
    verified: bool = False
    verification_method: Optional[str] = None
    steps_recorded: Optional[str] = None
    details: Optional[dict] = None


class PartyOut(BaseModel):
    id: uuid.UUID
    role: str
    name: str
    is_individual: bool
    bo_basis: Optional[str] = None
    ownership_pct: Optional[float] = None
    is_pep: bool
    pep_kind: Optional[str] = None
    sanctions_hit: bool
    verified: bool


class CddRequest(BaseModel):
    kyc_fields: Optional[dict] = None
    matter_id: Optional[uuid.UUID] = None
    source_of_funds: Optional[str] = None
    source_of_wealth: Optional[str] = None


class CddCheckOut(BaseModel):
    id: uuid.UUID
    level: str
    edd_reason: Optional[str] = None
    outcome: str
    created_at: datetime


class MatterCreate(BaseModel):
    client_id: uuid.UUID
    designated_service_key: str
    description: Optional[str] = None


class MatterOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    designated_service_key: str
    description: Optional[str] = None
    status: str
    cdd_gate_passed: bool
    cdd_gate_basis: Optional[str] = None
    risk_rating: Optional[str] = None
    opened_at: datetime


class ClientListItemOut(BaseModel):
    id: uuid.UUID
    type: str
    display_name: str
    risk_rating: Optional[str] = None
    cdd_status: str
    is_pep: bool
    sanctions_hit: bool


class ClientDetailOut(BaseModel):
    id: uuid.UUID
    type: str
    display_name: str
    status: str
    risk_rating: Optional[str] = None
    cdd_status: str
    is_pep: bool
    pep_kind: Optional[str] = None
    sanctions_hit: bool
    adverse_media_hit: bool
    source_of_funds: Optional[str] = None
    source_of_wealth: Optional[str] = None
    parties: List[PartyOut]
    matters: List[MatterOut]
    cdd_checks: List[CddCheckOut]


class CatalogueItem(BaseModel):
    key: str
    label: str
    customer: Optional[str] = None


class ClientsMetaOut(BaseModel):
    customer_types: List[CatalogueItem]
    designated_services: List[CatalogueItem]


# ----- Reporting & record keeping -----

class ReportCreate(BaseModel):
    type: str  # smr | ttr | ifti | annual_compliance | cross_border_bni
    related_client_id: Optional[uuid.UUID] = None
    related_matter_id: Optional[uuid.UUID] = None
    payload: Optional[dict] = None
    tf: bool = False  # SMR: terrorism-financing suspicion -> 24h deadline
    lpp_claimed: bool = False
    amount: Optional[float] = None  # TTR: physical-currency value
    reporting_period_end: Optional[str] = None  # annual report period end (ISO date)


class ReportUpdate(BaseModel):
    payload: Optional[dict] = None
    status: Optional[str] = None  # draft | ready | lodged | not_required
    reference_number: Optional[str] = None
    lpp_claimed: Optional[bool] = None
    lpp_form_ref: Optional[str] = None


class ReportOut(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    related_client_id: Optional[uuid.UUID] = None
    related_matter_id: Optional[uuid.UUID] = None
    deadline_basis: Optional[str] = None
    lpp_claimed: bool
    lpp_form_ref: Optional[str] = None
    due_at: Optional[datetime] = None
    lodged_at: Optional[datetime] = None
    reference_number: Optional[str] = None
    created_at: datetime


class DecisionRequest(BaseModel):
    reasonable_grounds: bool
    reasoning: Optional[str] = None
    client_id: Optional[uuid.UUID] = None
    matter_id: Optional[uuid.UUID] = None


class RecordOut(BaseModel):
    id: uuid.UUID
    category: str
    entity_type: Optional[str] = None
    retention_basis: str
    basis_date: Optional[str] = None
    retention_until: Optional[str] = None
    immutable: bool
    created_at: datetime
