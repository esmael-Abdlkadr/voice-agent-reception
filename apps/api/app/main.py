"""FastAPI app entrypoint for the voice-AI ops console."""
from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.db import SessionFactory
from app.models import User
from app.routers import agents, analytics, auth, calls, events, health, knowledge, livekit, tools, users, workspaces
from app.services import auth_service
from app.services.events import set_event_loop

log = logging.getLogger(__name__)


app = FastAPI(title="VoiceOps API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(agents.router)
app.include_router(knowledge.router)
app.include_router(tools.router)
app.include_router(calls.router)
app.include_router(analytics.router)
app.include_router(events.router)
app.include_router(livekit.router)


@app.on_event("startup")
async def capture_event_loop() -> None:
    """Capture the running event loop so sync routes can publish into it."""
    set_event_loop(asyncio.get_running_loop())


@app.on_event("startup")
def seed_admin() -> None:
    """Ensure a superuser exists so the operator can log in on first boot.

    Idempotent: only creates the seed admin if no superuser is present yet.
    """
    with SessionFactory() as session:
        has_superuser = session.execute(
            select(User).where(User.is_superuser.is_(True)).limit(1)
        ).first()
        if has_superuser:
            return
        admin = User(
            email=settings.seed_admin_email.lower(),
            name="VoiceOps Admin",
            password_hash=auth_service.hash_password(settings.seed_admin_password),
            is_superuser=True,
            status="active",
        )
        session.add(admin)
        session.commit()
        log.info("Seeded superuser %s", admin.email)
