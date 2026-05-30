"""FastAPI app entrypoint for the voice-AI ops console."""
from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.db import SessionFactory
from app.models import User, Workspace, WorkspaceMember
from app.routers import agents, auth, calls, events, health, internal, knowledge, livekit, phone_numbers, reservations, tools, users, workspaces
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
app.include_router(phone_numbers.router)
app.include_router(reservations.router)
app.include_router(calls.router)
app.include_router(internal.router)
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


# Demo non-superuser accounts so the role-based experience is testable.
# (email, name, password, workspace role)
_SEED_MEMBERS = [
    ("manager@voiceops.dev", "Workspace Manager", "manager-dev", "admin"),
    ("viewer@voiceops.dev", "Read-only Viewer", "viewer-dev", "viewer"),
]


@app.on_event("startup")
def seed_role_users() -> None:
    """Create a manager (admin) and a viewer, and add them to the first
    workspace with their role. Idempotent. Skips membership if no workspace
    exists yet."""
    with SessionFactory() as session:
        workspace = session.execute(
            select(Workspace).order_by(Workspace.id).limit(1)
        ).scalar_one_or_none()
        for email, name, password, role in _SEED_MEMBERS:
            user = session.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()
            if user is None:
                user = User(
                    email=email,
                    name=name,
                    password_hash=auth_service.hash_password(password),
                    is_superuser=False,
                    status="active",
                )
                session.add(user)
                session.flush()
                log.info("Seeded user %s (%s)", email, role)
            if workspace is not None:
                member = session.execute(
                    select(WorkspaceMember).where(
                        WorkspaceMember.user_id == user.id,
                        WorkspaceMember.workspace_id == workspace.id,
                    )
                ).scalar_one_or_none()
                if member is None:
                    session.add(
                        WorkspaceMember(
                            user_id=user.id, workspace_id=workspace.id, role=role
                        )
                    )
        session.commit()
