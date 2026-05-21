from fastapi import APIRouter, Depends, HTTPException

from app.models import AgentMessageCreate, AgentSessionCreate, CallSession
from app.services import agent_service, auth_service, store

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/session")
def create_agent_session(payload: AgentSessionCreate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> CallSession:
    return agent_service.create_session(payload.direction, payload.contact_id, payload.campaign_id)


@router.post("/message")
def send_agent_message(payload: AgentMessageCreate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> dict:
    if payload.session_id not in store.calls:
        raise HTTPException(status_code=404, detail="Call session not found")
    return agent_service.handle_message(payload)
