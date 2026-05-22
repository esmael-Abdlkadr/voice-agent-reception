"""Server-Sent Events endpoint streaming live call activity to the dashboard.

Browsers' EventSource API can't send a custom Authorization header, so we
accept the bearer token as a query string param (`?token=...`). This works
fine over HTTPS in production; over plain HTTP only on localhost.

The stream:
  1. On connect, sends a snapshot of every active call across the user's
     workspaces (events of type `call`).
  2. Then forwards every subsequently-published call event whose
     `workspace_id` is one the user belongs to.

A heartbeat comment is emitted every 25s to keep proxies from closing
idle connections.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionFactory, get_session
from app.models import Call, User, WorkspaceMember
from app.schemas import CallSummary
from app.services import auth_service
from app.services.events import subscribe

log = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


def _allowed_workspace_ids(user: User) -> set[int]:
    """Workspaces the user is allowed to see events for."""
    with SessionFactory() as session:
        memberships = session.execute(
            select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user.id)
        ).scalars().all()
    return set(memberships)


def _current_user_from_token(
    token: str = Query(..., description="Bearer token (EventSource can't send headers)"),
    session: Session = Depends(get_session),
) -> User:
    """Re-implements the bearer-token check using a query param token. We
    can't reuse auth_service.current_user because that requires an
    Authorization header that EventSource never sends."""
    user_id = auth_service._tokens.get(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    user = session.get(User, user_id)
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active"
        )
    return user


def _snapshot_active_calls(allowed_ws: set[int]) -> list[dict]:
    """Active calls across every workspace the user can see, freshly read
    from the DB so reconnect-after-page-refresh works."""
    if not allowed_ws:
        return []
    with SessionFactory() as session:
        rows = session.execute(
            select(Call)
            .where(Call.workspace_id.in_(allowed_ws), Call.status == "active")
            .order_by(Call.started_at.desc())
        ).scalars().all()
    return [
        {
            "type": "call",
            "workspace_id": call.workspace_id,
            "data": CallSummary.model_validate(call).model_dump(mode="json"),
        }
        for call in rows
    ]


@router.get("")
async def stream(user: User = Depends(_current_user_from_token)) -> StreamingResponse:
    allowed = _allowed_workspace_ids(user)

    async def gen() -> AsyncIterator[bytes]:
        # 1) Snapshot
        yield b": connected\n\n"
        for event in _snapshot_active_calls(allowed):
            yield _sse_data(event)

        # 2) Live stream with heartbeat
        sub = subscribe()

        try:
            while True:
                try:
                    event = await asyncio.wait_for(sub.__anext__(), timeout=25.0)
                except asyncio.TimeoutError:
                    yield b": ping\n\n"
                    continue
                except StopAsyncIteration:
                    break
                if event.get("workspace_id") in allowed:
                    yield _sse_data(event)
        finally:
            await sub.aclose()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # disables nginx buffering if present
            "Connection": "keep-alive",
        },
    )


def _sse_data(event: dict) -> bytes:
    return f"data: {json.dumps(event)}\n\n".encode("utf-8")
