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
    full_name: str
    role: str
    firm_id: uuid.UUID


class FirmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class UserWithFirm(UserOut):
    firm: FirmOut


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ----- Dashboard -----

class PendingActionOut(BaseModel):
    id: uuid.UUID
    kind: str  # "approval" | "deadline"
    title: str
    why: str
    estimate_label: Optional[str] = None
    action_label: str
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


class RiskAssessmentOut(BaseModel):
    id: uuid.UUID
    status: str
    overall_rating: str
    summary: str
    next_review_due: Optional[datetime] = None
    updated_at: datetime
    created_at: datetime
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    senior_manager_name: str
    services: List[RiskItemOut]
    client_types: List[RiskItemOut]
    channels: List[RiskItemOut]
    countries: List[RiskItemOut]
