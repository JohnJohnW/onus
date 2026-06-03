"""Pydantic request/response schemas for the Onus API."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# A pragmatic email shape check (one @, a dot in the domain, no whitespace). Avoids a
# new dependency while rejecting obviously invalid addresses like "notanemail".
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _check_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("A valid email address is required.")
    return value


# ----- Auth -----

class SignupRequest(BaseModel):
    firm_name: str = Field(min_length=1)
    full_name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    password: str = Field(min_length=12, description="Minimum 12 characters.")

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        return _check_email(v)


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
    is_active: bool = True


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
    management_level: bool = False
    is_australian_resident: bool = False
    fit_and_proper_considered: bool = False
    qualifies_reason: Optional[str] = None


class GovernanceAssignRequest(BaseModel):
    role: str  # governing_body | senior_manager | compliance_officer | independent_evaluator
    user_id: uuid.UUID
    qualifies_reason: Optional[str] = None
    management_level: bool = False
    is_australian_resident: bool = False
    fit_and_proper_considered: bool = False


class FirmSettingsOut(BaseModel):
    firm: FirmOut
    users: List[UserOut]
    governance_roles: List[GovernanceRoleOut]


class AuditLogOut(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
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


class ProgramChangeCreate(BaseModel):
    entity_type: str  # risk_assessment | policy | program
    change_summary: str
    trigger: str = "other"
    is_material: bool = False


class ProgramChangeOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    change_summary: str
    trigger: str
    is_material: bool
    documented: bool
    due_at: Optional[datetime] = None
    changed_at: datetime


class ReviewTriggerCreate(BaseModel):
    trigger_type: str
    description: Optional[str] = None


class ReviewTriggerOut(BaseModel):
    id: uuid.UUID
    trigger_type: str
    description: Optional[str] = None
    status: str
    review_required_by: Optional[datetime] = None
    created_at: datetime


class ProgramLifecycleOut(BaseModel):
    next_review_due: Optional[datetime] = None
    status: str
    open_triggers: List[ReviewTriggerOut]
    changes: List[ProgramChangeOut]


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


class AlertOut(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    indicator_key: str
    indicator_group: str
    severity: str
    narrative: Optional[str] = None
    status: str
    smr_report_id: Optional[uuid.UUID] = None
    created_at: datetime


class AlertCreate(BaseModel):
    client_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    indicator_key: str
    severity: str = "medium"
    narrative: Optional[str] = None


class ScanResultOut(BaseModel):
    raised: int
    alerts: List["AlertOut"]


class IndicatorOut(BaseModel):
    group: str
    group_label: str
    key: str
    label: str


class AlertEscalateRequest(BaseModel):
    tf: bool = False
    lpp_claimed: bool = False
    reasoning: Optional[str] = None


class AlertDismissRequest(BaseModel):
    reasoning: Optional[str] = None


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
    alerts: List[AlertOut] = []


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
    grounds: Optional[str] = None  # SMR grounds-for-suspicion (merged into payload)
    status: Optional[str] = None  # draft | ready | lodged | not_required
    reference_number: Optional[str] = None
    lpp_claimed: Optional[bool] = None
    lpp_form_ref: Optional[str] = None


class AnnualSummaryOut(BaseModel):
    """A data-driven draft to help complete AUSTRAC's annual compliance report. The
    counts are gathered from the firm's own records for the reporting period; it is a
    starting point for the principal to review, not the official AUSTRAC form."""
    period_start: str
    period_end: str
    program_approved: bool = False
    program_approved_at: Optional[datetime] = None
    risk_rating: Optional[str] = None
    last_evaluation_at: Optional[datetime] = None
    smr_lodged: int = 0
    ttr_lodged: int = 0
    ivts_lodged: int = 0
    alerts_raised: int = 0
    alerts_escalated: int = 0
    material_changes: int = 0
    clients_onboarded: int = 0
    matters_opened: int = 0
    open_alerts: int = 0
    pending_deadlines: int = 0
    unresolved_triggers: int = 0


class ReportOut(BaseModel):
    id: uuid.UUID
    type: str
    status: str
    related_client_id: Optional[uuid.UUID] = None
    related_matter_id: Optional[uuid.UUID] = None
    related_alert_id: Optional[uuid.UUID] = None
    grounds: Optional[str] = None  # SMR grounds-for-suspicion (from payload)
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


# ----- Independent evaluation -----

class EvaluationScheduleRequest(BaseModel):
    frequency_months: Optional[int] = None
    frequency_rationale: Optional[str] = None
    is_first_evaluation: bool = False
    scheduled_for: Optional[str] = None  # ISO date


class EvaluatorRequest(BaseModel):
    name: str
    kind: str = "external"  # internal | external
    is_compliance_officer: bool = False
    independence_confirmed: bool = False
    independence_checklist: Optional[dict] = None
    suitability_scorecard: Optional[dict] = None
    selection_rationale: Optional[str] = None


class FindingIn(BaseModel):
    area: str  # risk_assessment | policy | compliance
    is_adverse: bool = False
    description: str
    remediation_action: Optional[str] = None


class EvaluationReportRequest(BaseModel):
    summary_of_process: Optional[str] = None
    aspects_reviewed: Optional[str] = None
    method: Optional[str] = None
    findings_risk_assessment: Optional[str] = None
    findings_policy_design: Optional[str] = None
    findings_compliance: Optional[str] = None
    items_tested: Optional[str] = None
    files_sampled: Optional[str] = None
    sampling_method: Optional[str] = None
    document_ref: Optional[str] = None
    findings: List[FindingIn] = []


class FindingUpdate(BaseModel):
    status: Optional[str] = None  # open | in_progress | done | wont_fix
    remediation_action: Optional[str] = None
    wont_fix_reason: Optional[str] = None


class EvaluatorOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    independence_confirmed: bool
    is_compliance_officer: bool
    selection_rationale: Optional[str] = None


class FindingOut(BaseModel):
    id: uuid.UUID
    area: str
    is_adverse: bool
    description: str
    remediation_action: Optional[str] = None
    status: str
    wont_fix_reason: Optional[str] = None


class EvaluationOut(BaseModel):
    id: uuid.UUID
    status: str
    frequency_months: Optional[int] = None
    frequency_rationale: Optional[str] = None
    is_first_evaluation: bool
    statutory_deadline: Optional[str] = None
    scheduled_for: Optional[str] = None
    report_received_at: Optional[datetime] = None
    distributed_to_governing_body_at: Optional[datetime] = None
    distributed_to_senior_manager_at: Optional[datetime] = None
    evaluator: Optional[EvaluatorOut] = None
    has_report: bool = False
    findings: List[FindingOut] = []


class EvaluationsOut(BaseModel):
    first_evaluation_deadline: Optional[str] = None
    enrolment_known: bool = False
    evaluations: List[EvaluationOut]


# ----- Sanctions screening -----


class SanctionsStatusOut(BaseModel):
    list_type: str = "sanctions"  # sanctions | pep
    loaded: bool = False
    source: Optional[str] = None
    origin: Optional[str] = None  # auto_fetch | manual_upload
    fetched_at: Optional[datetime] = None
    entry_count: int = 0
    content_hash: Optional[str] = None
    url_configured: bool = False


class ScreenRequest(BaseModel):
    name: str
    list_type: str = "sanctions"  # sanctions | pep
    subject_type: Optional[str] = None  # client | party | adhoc
    subject_id: Optional[uuid.UUID] = None
    threshold: Optional[float] = None
    record: bool = False


class ScreenCandidate(BaseModel):
    reference: Optional[str] = None
    entity_type: str
    primary_name: str
    matched_name: str
    score: float
    aliases: Optional[List[str]] = None
    dob: Optional[str] = None
    citizenship: Optional[str] = None
    listing_info: Optional[str] = None


class ScreenResultOut(BaseModel):
    query_name: str
    list_type: str = "sanctions"
    list_fetched_at: Optional[datetime] = None
    match_count: int
    candidates: List[ScreenCandidate]


# ----- Matter classification (AI) -----


class MatterClassifyRequest(BaseModel):
    description: str
    client_id: Optional[uuid.UUID] = None


class MatterClassifyOut(BaseModel):
    service_key: Optional[str] = None
    service_label: Optional[str] = None
    is_designated_service: Optional[bool] = None
    customer: Optional[str] = None
    cdd_tier: Optional[str] = None
    rationale: str = ""


# ----- Documents / evidence -----


class DocumentOut(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    filename: str
    content_type: Optional[str] = None
    size_bytes: int
    uploaded_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime


# ----- User / team management -----


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    role: str = "member"  # admin | member

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        return _check_email(v)


class UserRoleUpdate(BaseModel):
    role: Optional[str] = None  # admin | member
    is_active: Optional[bool] = None


class UserCreatedOut(BaseModel):
    user: UserOut
    temporary_password: str  # shown once; the colleague changes it after first login


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, description="Minimum 12 characters.")


# ----- Data residency attestation -----

class AttestationIn(BaseModel):
    data_region: str = Field(min_length=1)  # where data resides, e.g. "Australia (Sydney)"
    hosting_provider: Optional[str] = None
    cross_border: bool = False
    dpa_in_place: bool = False
    approved_by_name: Optional[str] = None
    attested_on: Optional[str] = None  # ISO date
    notes: Optional[str] = None


class AttestationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    data_region: str
    hosting_provider: Optional[str] = None
    cross_border: bool
    dpa_in_place: bool
    approved_by_name: Optional[str] = None
    attested_on: Optional[date] = None
    notes: Optional[str] = None
    updated_at: datetime


# ----- Demo expression of interest -----

class EoiIn(BaseModel):
    email: str = Field(min_length=3)
    name: Optional[str] = None
    firm_name: Optional[str] = None
    note: Optional[str] = None

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        return _check_email(v)
