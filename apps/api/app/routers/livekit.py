"""LiveKit access token endpoint.

The browser playground hits this to obtain a short-lived JWT it can use to join
a LiveKit room. The voice-agent worker (apps/voice-agent) auto-joins the same
room and runs the receptionist pipeline.
"""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, HTTPException
from livekit import api
from pydantic import BaseModel

router = APIRouter(prefix="/livekit", tags=["livekit"])


class TokenRequest(BaseModel):
    identity: str | None = None
    room: str | None = None


class TokenResponse(BaseModel):
    token: str
    url: str
    room: str
    identity: str


@router.post("/token", response_model=TokenResponse)
def create_token(req: TokenRequest | None = None) -> TokenResponse:
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    livekit_url = os.getenv("LIVEKIT_URL")
    if not (api_key and api_secret and livekit_url):
        raise HTTPException(
            status_code=503,
            detail="LiveKit is not configured. Set LIVEKIT_URL, LIVEKIT_API_KEY, "
            "and LIVEKIT_API_SECRET in .env.",
        )

    req = req or TokenRequest()
    identity = req.identity or f"caller-{uuid.uuid4().hex[:8]}"
    room = req.room or f"brightcare-{uuid.uuid4().hex[:8]}"

    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(api.VideoGrants(room_join=True, room=room))
        .to_jwt()
    )

    return TokenResponse(token=token, url=livekit_url, room=room, identity=identity)
