"""Auth endpoints: login + current-user context."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User, Workspace, WorkspaceMember
from app.schemas import (
    CurrentUserContext,
    LoginRequest,
    TokenResponse,
    UserPublic,
    WorkspaceSummary,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    token, user = auth_service.login(session, payload.email, payload.password)
    return TokenResponse(access_token=token, user=UserPublic.model_validate(user))


@router.get("/me", response_model=CurrentUserContext)
def me(
    user: User = Depends(auth_service.current_user),
    session: Session = Depends(get_session),
) -> CurrentUserContext:
    rows = session.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.name)
    ).all()
    workspaces = [
        WorkspaceSummary(id=ws.id, slug=ws.slug, name=ws.name, role=role)
        for ws, role in rows
    ]
    return CurrentUserContext(
        user=UserPublic.model_validate(user),
        workspaces=workspaces,
    )
