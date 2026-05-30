"""Call persistence + read endpoints scoped per workspace.

The voice-agent worker POSTs an "active" Call at session start, then POSTs
again at session end with the full transcript. Same endpoint, upsert by
livekit_room_id. Each create or material update fans out to the live event
stream so the Live dashboard can update without polling.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Agent, Call, CallToolCall, CallTurn, User, Workspace
from app.schemas import CallCreate, CallDetail, CallStreamEvent, CallSummary
from app.services import auth_service
from app.services.events import publish_threadsafe

router = APIRouter(prefix="/workspaces/{workspace_id}/calls", tags=["calls"])


def _publish_call(workspace_id: int, call: Call) -> None:
    publish_threadsafe(
        {
            "type": "call",
            "workspace_id": workspace_id,
            "data": CallSummary.model_validate(call).model_dump(mode="json"),
        }
    )


@router.get("", response_model=list[CallSummary])
def list_calls(
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    viewer: "User" = Depends(auth_service.current_user),
    session: Session = Depends(get_session),
) -> list[CallSummary]:
    stmt = select(Call).where(Call.workspace_id == workspace.id)
    if not auth_service.is_workspace_manager(session, viewer, workspace.id):
        stmt = stmt.where(Call.owner_user_id == viewer.id)
    calls = session.execute(stmt.order_by(Call.started_at.desc()).limit(200)).scalars().all()
    return [CallSummary.model_validate(c) for c in calls]


@router.post("", response_model=CallDetail, status_code=status.HTTP_201_CREATED)
def upsert_call(
    payload: CallCreate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    caller: "User | None" = Depends(auth_service.optional_user),
    session: Session = Depends(get_session),
) -> CallDetail:
    """Create or update a call, keyed by livekit_room_id.

    The worker calls this twice:
      1. At session start: minimal payload, status="active"
      2. At session end: full payload (turns + tool_calls), status="completed"

    The end-of-call POST replaces turns + tool_calls (the worker has the
    canonical list).
    """
    if payload.agent_id is not None:
        agent = session.get(Agent, payload.agent_id)
        if agent is None or agent.workspace_id != workspace.id:
            raise HTTPException(status_code=400, detail="agent_id is not in this workspace")

    existing = session.execute(
        select(Call).where(
            Call.workspace_id == workspace.id,
            Call.livekit_room_id == payload.livekit_room_id,
        )
    ).scalar_one_or_none()

    if existing is None:
        call = Call(
            workspace_id=workspace.id,
            owner_user_id=caller.id if caller else None,
            agent_id=payload.agent_id,
            livekit_room_id=payload.livekit_room_id,
            caller_identity=payload.caller_identity,
            started_at=payload.started_at,
            ended_at=payload.ended_at,
            status=payload.status,
            outcome=payload.outcome,
            escalation_reason=payload.escalation_reason,
            recording_url=payload.recording_url,
            duration_ms=payload.duration_ms,
        )
        session.add(call)
        session.flush()
    else:
        call = existing
        call.agent_id = payload.agent_id
        call.caller_identity = payload.caller_identity
        call.started_at = payload.started_at
        if payload.ended_at is not None:
            call.ended_at = payload.ended_at
        call.status = payload.status
        if payload.outcome is not None:
            call.outcome = payload.outcome
        if payload.escalation_reason is not None:
            call.escalation_reason = payload.escalation_reason
        if payload.recording_url is not None:
            call.recording_url = payload.recording_url
        if payload.duration_ms is not None:
            call.duration_ms = payload.duration_ms

    if payload.turns:
        session.execute(delete(CallTurn).where(CallTurn.call_id == call.id))
        for turn in payload.turns:
            session.add(
                CallTurn(
                    call_id=call.id,
                    role=turn.role,
                    text=turn.text,
                    ts_ms=turn.ts_ms,
                    audio_ms=turn.audio_ms,
                )
            )
    if payload.tool_calls:
        session.execute(delete(CallToolCall).where(CallToolCall.call_id == call.id))
        for tc in payload.tool_calls:
            session.add(
                CallToolCall(
                    call_id=call.id,
                    tool_name=tc.tool_name,
                    args_json=tc.args_json,
                    result_json=tc.result_json,
                    ts_ms=tc.ts_ms,
                    duration_ms=tc.duration_ms,
                    status=tc.status,
                )
            )

    session.commit()
    session.refresh(call)
    _publish_call(workspace.id, call)
    return CallDetail.model_validate(call)


@router.get("/{call_id}", response_model=CallDetail)
def get_call(
    call_id: int,
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> CallDetail:
    call = session.get(Call, call_id)
    if call is None or call.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Call not found")
    return CallDetail.model_validate(call)


@router.post("/stream", status_code=status.HTTP_202_ACCEPTED)
def stream_event(
    payload: CallStreamEvent,
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> dict:
    """Receive a single mid-call event from the voice worker.

    Turns are appended to the DB so a refresh mid-call still shows the
    partial transcript; both turns and tool calls are fanned out over SSE
    so the dashboard updates live. No-op (not an error) if the call row
    doesn't exist yet — the session-start POST may not have landed.
    """
    call = session.execute(
        select(Call).where(
            Call.workspace_id == workspace.id,
            Call.livekit_room_id == payload.livekit_room_id,
        )
    ).scalar_one_or_none()
    if call is None:
        return {"ok": False, "reason": "call_not_found"}

    if payload.kind == "turn" and payload.text and payload.role:
        session.add(
            CallTurn(
                call_id=call.id,
                role=payload.role,
                text=payload.text,
                ts_ms=payload.ts_ms,
                audio_ms=None,
            )
        )
        session.commit()
        publish_threadsafe(
            {
                "type": "call_turn",
                "workspace_id": workspace.id,
                "call_id": call.id,
                "data": {
                    "role": payload.role,
                    "text": payload.text,
                    "ts_ms": payload.ts_ms,
                },
            }
        )
    elif payload.kind == "tool_call" and payload.tool_name:
        publish_threadsafe(
            {
                "type": "call_tool",
                "workspace_id": workspace.id,
                "call_id": call.id,
                "data": {
                    "tool_name": payload.tool_name,
                    "status": payload.status or "success",
                    "ts_ms": payload.ts_ms,
                    "duration_ms": payload.duration_ms,
                },
            }
        )

    return {"ok": True}
