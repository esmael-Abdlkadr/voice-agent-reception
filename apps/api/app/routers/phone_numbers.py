"""Phone number management scoped per workspace.

Operators register the PSTN numbers they've provisioned (Twilio etc.) and
point each at an agent. The voice worker resolves the dialed number to an
agent at call time via /internal/resolve-number.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Agent, PhoneNumber, Workspace
from app.schemas import PhoneNumberCreate, PhoneNumberDetail, PhoneNumberUpdate
from app.services import auth_service

router = APIRouter(prefix="/workspaces/{workspace_id}/phone-numbers", tags=["phone-numbers"])


def _validate_agent(session: Session, workspace_id: int, agent_id: int | None) -> None:
    if agent_id is None:
        return
    agent = session.get(Agent, agent_id)
    if agent is None or agent.workspace_id != workspace_id:
        raise HTTPException(status_code=400, detail="agent_id is not in this workspace")


@router.get("", response_model=list[PhoneNumberDetail])
def list_numbers(
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> list[PhoneNumberDetail]:
    rows = (
        session.execute(
            select(PhoneNumber)
            .where(PhoneNumber.workspace_id == workspace.id)
            .order_by(PhoneNumber.created_at)
        )
        .scalars()
        .all()
    )
    return [PhoneNumberDetail.model_validate(n) for n in rows]


@router.post("", response_model=PhoneNumberDetail, status_code=status.HTTP_201_CREATED)
def create_number(
    payload: PhoneNumberCreate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> PhoneNumberDetail:
    existing = session.execute(
        select(PhoneNumber).where(PhoneNumber.e164 == payload.e164)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"{payload.e164} is already registered"
            + (" in this workspace" if existing.workspace_id == workspace.id else " in another workspace"),
        )
    _validate_agent(session, workspace.id, payload.agent_id)
    number = PhoneNumber(
        e164=payload.e164,
        label=payload.label,
        agent_id=payload.agent_id,
        workspace_id=workspace.id,
    )
    session.add(number)
    session.commit()
    session.refresh(number)
    return PhoneNumberDetail.model_validate(number)


@router.patch("/{number_id}", response_model=PhoneNumberDetail)
def update_number(
    number_id: int,
    payload: PhoneNumberUpdate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> PhoneNumberDetail:
    number = session.get(PhoneNumber, number_id)
    if number is None or number.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Phone number not found")
    fields = payload.model_dump(exclude_unset=True)
    if "agent_id" in fields:
        _validate_agent(session, workspace.id, fields["agent_id"])
    for key, value in fields.items():
        setattr(number, key, value)
    session.commit()
    session.refresh(number)
    return PhoneNumberDetail.model_validate(number)


@router.delete("/{number_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_number(
    number_id: int,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> None:
    number = session.get(PhoneNumber, number_id)
    if number is None or number.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Phone number not found")
    session.delete(number)
    session.commit()
