"""LiveKit access token endpoint.

The browser dashboard hits this to obtain a short-lived JWT it can use to join
a LiveKit room. The voice-agent worker (apps/voice-agent) auto-joins the same
room and runs the agent pipeline configured for the requested workspace.

The token's participant metadata embeds:
  - workspace_id: which tenant the call is for
  - agent_id: which Agent config to load (optional; worker picks the first
    active agent in the workspace if omitted)
  - api_token: the operator's bearer token, so the worker can call back to
    the API (load agent config, search KB, persist the call) on behalf of
    the user who started the call
  - api_base_url: where to call back

The api_token rides along with the LiveKit token; it lives only as long as
the operator's session does and is only visible to participants inside the
room (the worker is the only other participant in V1).
"""
from __future__ import annotations

import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from livekit import api
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Agent, User, Workspace
from app.services import auth_service

router = APIRouter(prefix="/livekit", tags=["livekit"])

_security = HTTPBearer(auto_error=True)


class TokenRequest(BaseModel):
    workspace_id: int
    agent_id: int | None = None
    identity: str | None = None


class TokenResponse(BaseModel):
    token: str
    url: str
    room: str
    identity: str
    workspace_id: int
    agent_id: int | None


@router.post("/token", response_model=TokenResponse)
def create_token(
    req: TokenRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    user: User = Depends(auth_service.current_user),
    session: Session = Depends(get_session),
) -> TokenResponse:
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")
    if not (api_key and api_secret and livekit_url):
        raise HTTPException(
            status_code=503,
            detail="LiveKit is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, "
            "and LIVEKIT_API_SECRET in .env.",
        )

    workspace, _role = auth_service._resolve_member_role(session, user, req.workspace_id)

    agent: Agent | None = None
    if req.agent_id is not None:
        agent = session.get(Agent, req.agent_id)
        if agent is None or agent.workspace_id != workspace.id:
            raise HTTPException(status_code=404, detail="Agent not found in workspace")
    else:
        agent = session.execute(
            select(Agent)
            .where(Agent.workspace_id == workspace.id, Agent.is_active.is_(True))
            .order_by(Agent.created_at)
            .limit(1)
        ).scalar_one_or_none()
        if agent is None:
            raise HTTPException(
                status_code=400,
                detail="No active agent in this workspace. Create one on the Agent page.",
            )

    identity = req.identity or f"caller-{uuid.uuid4().hex[:8]}"
    room = f"ws{workspace.id}-{uuid.uuid4().hex[:10]}"

    metadata = json.dumps(
        {
            "workspace_id": workspace.id,
            "agent_id": agent.id,
            "api_base_url": os.getenv("API_PUBLIC_URL", "http://localhost:8000"),
            "api_token": credentials.credentials,
        }
    )

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_metadata(metadata)
        .with_grants(api.VideoGrants(room_join=True, room=room))
        .to_jwt()
    )

    return TokenResponse(
        token=token,
        url=livekit_url,
        room=room,
        identity=identity,
        workspace_id=workspace.id,
        agent_id=agent.id,
    )
