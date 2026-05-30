"""Internal endpoints the voice worker calls with the service key.

These exist because a phone call has no logged-in operator — the worker
needs a system-authenticated way to resolve which agent answers a dialed
number. Guarded by the shared SERVICE_API_KEY (see auth_service).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Agent, PhoneNumber
from app.schemas import AgentDetail, ResolvedNumber
from app.services import auth_service

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    dependencies=[Depends(auth_service.require_service_key)],
)


@router.get("/resolve-number", response_model=ResolvedNumber)
def resolve_number(
    e164: str = Query(..., description="Dialed number in E.164, e.g. +19859996931"),
    session: Session = Depends(get_session),
) -> ResolvedNumber:
    """Map a dialed phone number to the workspace + agent that should answer."""
    number = session.execute(
        select(PhoneNumber).where(PhoneNumber.e164 == e164)
    ).scalar_one_or_none()
    if number is None or not number.is_active:
        raise HTTPException(status_code=404, detail=f"No active route for {e164}")

    agent: Agent | None = None
    if number.agent_id is not None:
        agent = session.get(Agent, number.agent_id)
    if agent is None or agent.workspace_id != number.workspace_id:
        agent = session.execute(
            select(Agent)
            .where(Agent.workspace_id == number.workspace_id, Agent.is_active.is_(True))
            .order_by(Agent.created_at)
            .limit(1)
        ).scalar_one_or_none()
    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"{e164} routes to workspace {number.workspace_id} but it has no active agent",
        )

    return ResolvedNumber(
        workspace_id=number.workspace_id,
        agent_id=agent.id,
        agent=AgentDetail.model_validate(agent),
    )
