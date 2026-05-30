"""Pydantic request/response schemas for the HTTP API.

Kept separate from SQLAlchemy ORM models in app/models.py. ORM models are
the persistence shape; these are the wire shape.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

WorkspaceRole = Literal["owner", "admin", "viewer"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    status: str
    is_superuser: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserPublic


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    is_superuser: bool = False


class UserUpdate(BaseModel):
    name: Optional[str] = None
    password: Optional[str] = None
    status: Optional[str] = None
    is_superuser: Optional[bool] = None


class WorkspaceSummary(BaseModel):
    """Light shape used in the sidebar + /auth/me."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    role: WorkspaceRole = Field(description="Caller's role in this workspace")


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional; auto-generated from name if omitted.",
    )


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, max_length=64)


class WorkspaceDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    created_at: datetime
    created_by_user_id: int


class WorkspaceMemberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role: WorkspaceRole
    created_at: datetime
    user_email: str
    user_name: str


class WorkspaceMemberAdd(BaseModel):
    user_id: int
    role: WorkspaceRole = "viewer"


class WorkspaceMemberUpdate(BaseModel):
    role: WorkspaceRole


class CurrentUserContext(BaseModel):
    user: UserPublic
    workspaces: list[WorkspaceSummary]


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    persona_prompt: str = ""
    greeting: str = ""
    voice_id: str = ""
    voice_provider: str = "cartesia"
    llm_model: str = "llama-3.1-8b-instant"
    is_active: bool = True


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    persona_prompt: Optional[str] = None
    greeting: Optional[str] = None
    voice_id: Optional[str] = None
    voice_provider: Optional[str] = None
    llm_model: Optional[str] = None
    is_active: Optional[bool] = None


class AgentDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    persona_prompt: str
    greeting: str
    voice_id: str
    voice_provider: str
    llm_model: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


KnowledgeStatus = Literal["processing", "ready", "failed"]


class KnowledgeDocPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    filename: str
    content_type: str
    size_bytes: int
    status: KnowledgeStatus
    chunk_count: int
    created_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchHit(BaseModel):
    doc_id: int
    filename: str
    chunk_idx: int
    text: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    hits: list[KnowledgeSearchHit]


class ToolCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="snake_case identifier the LLM sees as the function name",
    )
    description: str = Field(
        min_length=1,
        max_length=2000,
        description="Helps the LLM decide when to call this tool. Be concrete.",
    )
    webhook_url: str = Field(min_length=1, max_length=1024)
    auth_header: Optional[str] = Field(default=None, max_length=1024)
    schema_json: dict = Field(
        default_factory=dict,
        description="Free-form JSON describing the args/result shape. Informational for the operator only.",
    )


class ToolUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None, min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$"
    )
    description: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    webhook_url: Optional[str] = Field(default=None, min_length=1, max_length=1024)
    auth_header: Optional[str] = Field(default=None, max_length=1024)
    schema_json: Optional[dict] = None


class ToolDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str
    webhook_url: str
    auth_header: Optional[str]
    schema_json: dict
    created_at: datetime


class ToolTestRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class ToolTestResponse(BaseModel):
    status_code: int
    response_body: str
    error: Optional[str] = None
    duration_ms: int


CallStatus = Literal["active", "completed", "failed", "escalated"]
TurnRole = Literal["user", "agent"]


class CallTurnCreate(BaseModel):
    role: TurnRole
    text: str
    ts_ms: int = Field(ge=0)
    audio_ms: Optional[int] = None


class CallToolCallCreate(BaseModel):
    tool_name: str
    args_json: dict = Field(default_factory=dict)
    result_json: dict = Field(default_factory=dict)
    ts_ms: int = Field(ge=0)
    duration_ms: int = Field(ge=0, default=0)
    status: Literal["success", "error"] = "success"


class CallCreate(BaseModel):
    agent_id: Optional[int] = None
    livekit_room_id: str
    caller_identity: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: CallStatus = "completed"
    outcome: Optional[str] = None
    escalation_reason: Optional[str] = None
    recording_url: Optional[str] = None
    duration_ms: Optional[int] = None
    turns: list[CallTurnCreate] = Field(default_factory=list)
    tool_calls: list[CallToolCallCreate] = Field(default_factory=list)


class CallTurnPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: TurnRole
    text: str
    ts_ms: int
    audio_ms: Optional[int]


class CallToolCallPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tool_name: str
    args_json: dict
    result_json: dict
    ts_ms: int
    duration_ms: int
    status: str


class CallSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    agent_id: Optional[int]
    livekit_room_id: str
    caller_identity: str
    started_at: datetime
    ended_at: Optional[datetime]
    status: str
    outcome: Optional[str]
    duration_ms: Optional[int]


class CallDetail(CallSummary):
    escalation_reason: Optional[str]
    recording_url: Optional[str]
    turns: list[CallTurnPublic]
    tool_calls: list[CallToolCallPublic]


class CallStreamEvent(BaseModel):
    """A single live event the worker emits while a call is in progress.

    `kind="turn"` carries role/text and is persisted to the DB immediately
    so a mid-call page refresh still shows the partial transcript. The
    end-of-call upsert later replaces the turn list with the canonical one.

    `kind="tool_call"` is published to the live stream only (the canonical
    tool-call records are written by the end-of-call upsert).
    """

    livekit_room_id: str
    kind: Literal["turn", "tool_call"]
    ts_ms: int = Field(ge=0)
    role: Optional[TurnRole] = None
    text: Optional[str] = None
    tool_name: Optional[str] = None
    status: Optional[Literal["success", "error"]] = None
    duration_ms: int = Field(ge=0, default=0)


class PhoneNumberCreate(BaseModel):
    e164: str = Field(
        min_length=4,
        max_length=32,
        pattern=r"^\+[1-9]\d{1,18}$",
        description="E.164 format, e.g. +19859996931",
    )
    label: str = ""
    agent_id: Optional[int] = None


class PhoneNumberUpdate(BaseModel):
    label: Optional[str] = None
    agent_id: Optional[int] = None
    is_active: Optional[bool] = None


class PhoneNumberDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    e164: str
    label: str
    provider: str
    workspace_id: int
    agent_id: Optional[int]
    is_active: bool
    created_at: datetime


class ResolvedNumber(BaseModel):
    """What the worker gets back when it resolves a dialed number — enough
    to run the call without an operator session."""

    workspace_id: int
    agent_id: int
    agent: AgentDetail


class ReservationCreate(BaseModel):
    guest_name: str = Field(min_length=1, max_length=255)
    guest_phone: Optional[str] = None
    check_in: date
    check_out: date
    room_type: str = ""
    num_guests: int = Field(default=1, ge=1, le=20)
    notes: str = ""
    call_id: Optional[int] = None


class ReservationUpdate(BaseModel):
    status: Optional[Literal["requested", "confirmed", "cancelled"]] = None


class ReservationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    guest_name: str
    guest_phone: Optional[str]
    check_in: date
    check_out: date
    room_type: str
    num_guests: int
    notes: str
    status: str
    call_id: Optional[int]
    created_at: datetime

