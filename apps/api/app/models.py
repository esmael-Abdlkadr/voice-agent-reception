"""SQLAlchemy 2.0 ORM models for the voice-AI ops console.

Schema mirrors the V1 design: an agency operator (User) belongs to many
client workspaces (Workspace) via WorkspaceMember, and each workspace owns
its own Agent configuration, KnowledgeDocs, Tools, EscalationRules, and
the Calls + CallTurns + CallToolCalls produced when callers interact with
that workspace's agent.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="active")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    memberships: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    members: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    knowledge_docs: Mapped[list["KnowledgeDoc"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    tools: Mapped[list["Tool"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    escalation_rules: Mapped[list["EscalationRule"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    calls: Mapped[list["Call"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id", name="uq_member_user_workspace"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped[User] = relationship(back_populates="memberships")
    workspace: Mapped[Workspace] = relationship(back_populates="members")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    persona_prompt: Mapped[str] = mapped_column(Text, default="")
    greeting: Mapped[str] = mapped_column(Text, default="")
    voice_id: Mapped[str] = mapped_column(String(128), default="")
    voice_provider: Mapped[str] = mapped_column(String(64), default="cartesia")
    llm_model: Mapped[str] = mapped_column(String(128), default="llama-3.1-8b-instant")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    workspace: Mapped[Workspace] = relationship(back_populates="agents")
    calls: Mapped[list["Call"]] = relationship(back_populates="agent")


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str] = mapped_column(String(128), default="")
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="processing")
    qdrant_collection: Mapped[str] = mapped_column(String(128), default="")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="knowledge_docs")


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    webhook_url: Mapped[str] = mapped_column(String(1024))
    schema_json: Mapped[dict] = mapped_column(JSON, default=dict)
    auth_header: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="tools")


class PhoneNumber(Base):
    """A PSTN number (E.164) routed to a workspace's agent.

    When a call arrives over SIP, the worker reads the dialed number and
    looks it up here to decide which workspace + agent should answer.
    The number is globally unique (one number routes to exactly one agent).
    """

    __tablename__ = "phone_numbers"

    id: Mapped[int] = mapped_column(primary_key=True)
    e164: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(255), default="")
    provider: Mapped[str] = mapped_column(String(32), default="twilio")
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class EscalationRule(Base):
    __tablename__ = "escalation_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    trigger: Mapped[str] = mapped_column(String(64))
    trigger_value: Mapped[str] = mapped_column(String(512), default="")
    action: Mapped[str] = mapped_column(String(64))
    action_target: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    workspace: Mapped[Workspace] = relationship(back_populates="escalation_rules")


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (
        Index("ix_calls_workspace_started", "workspace_id", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    livekit_room_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    caller_identity: Mapped[str] = mapped_column(String(255))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    outcome: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recording_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    workspace: Mapped[Workspace] = relationship(back_populates="calls")
    agent: Mapped[Optional[Agent]] = relationship(back_populates="calls")
    turns: Mapped[list["CallTurn"]] = relationship(
        back_populates="call", cascade="all, delete-orphan", order_by="CallTurn.ts_ms"
    )
    tool_calls: Mapped[list["CallToolCall"]] = relationship(
        back_populates="call", cascade="all, delete-orphan", order_by="CallToolCall.ts_ms"
    )


class CallTurn(Base):
    __tablename__ = "call_turns"
    __table_args__ = (Index("ix_call_turns_call_ts", "call_id", "ts_ms"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    ts_ms: Mapped[int] = mapped_column(Integer)
    audio_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    call: Mapped[Call] = relationship(back_populates="turns")


class CallToolCall(Base):
    __tablename__ = "call_tool_calls"
    __table_args__ = (Index("ix_call_tool_calls_call_ts", "call_id", "ts_ms"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[int] = mapped_column(ForeignKey("calls.id", ondelete="CASCADE"), index=True)
    tool_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tools.id", ondelete="SET NULL"), nullable=True
    )
    tool_name: Mapped[str] = mapped_column(String(128))
    args_json: Mapped[dict] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ts_ms: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="success")

    call: Mapped[Call] = relationship(back_populates="tool_calls")

class Reservation(Base):
    """A lightweight hotel reservation REQUEST taken by the voice agent.

    No live inventory: the agent records the guest's request (dates, room
    type, party size) and staff confirm it. check_in/check_out are calendar
    dates (a stay spans the nights between them).
    """

    __tablename__ = "reservations"
    __table_args__ = (Index("ix_reservations_ws_checkin", "workspace_id", "check_in"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    owner_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    guest_name: Mapped[str] = mapped_column(String(255))
    guest_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    check_in: Mapped[date] = mapped_column(Date, index=True)
    check_out: Mapped[date] = mapped_column(Date)
    room_type: Mapped[str] = mapped_column(String(128), default="")
    num_guests: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="requested")
    call_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("calls.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

