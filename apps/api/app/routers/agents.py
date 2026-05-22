"""Agent CRUD scoped per workspace.

A workspace may have multiple Agent configurations; the runtime (M4) will
pick the active one when a call comes in.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Agent, Workspace
from app.schemas import AgentCreate, AgentDetail, AgentUpdate
from app.services import auth_service

router = APIRouter(prefix="/workspaces/{workspace_id}/agents", tags=["agents"])


@router.get("", response_model=list[AgentDetail])
def list_agents(
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> list[AgentDetail]:
    agents = (
        session.execute(
            select(Agent).where(Agent.workspace_id == workspace.id).order_by(Agent.created_at)
        )
        .scalars()
        .all()
    )
    return [AgentDetail.model_validate(a) for a in agents]


@router.post("", response_model=AgentDetail, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> AgentDetail:
    agent = Agent(workspace_id=workspace.id, **payload.model_dump())
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return AgentDetail.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentDetail)
def get_agent(
    agent_id: int,
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> AgentDetail:
    agent = session.get(Agent, agent_id)
    if agent is None or agent.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentDetail.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentDetail)
def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> AgentDetail:
    agent = session.get(Agent, agent_id)
    if agent is None or agent.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(agent, key, value)
    session.commit()
    session.refresh(agent)
    return AgentDetail.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: int,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> None:
    agent = session.get(Agent, agent_id)
    if agent is None or agent.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    session.delete(agent)
    session.commit()
