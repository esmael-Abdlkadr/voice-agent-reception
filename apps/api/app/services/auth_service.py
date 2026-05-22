"""Authentication and workspace-scoped authorization helpers.

Tokens are in-memory only (process-local dict). Good enough for V1 / single
worker; we'll move to JWT or a DB-backed session table when we need
horizontal scaling.
"""
from __future__ import annotations

import secrets
from typing import Literal

import bcrypt
from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User, Workspace, WorkspaceMember

WorkspaceRole = Literal["owner", "admin", "viewer"]
_ROLE_RANK = {"viewer": 1, "admin": 2, "owner": 3}

_security = HTTPBearer(auto_error=False)
_tokens: dict[str, int] = {}  # token -> user_id


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def login(session: Session, email: str, password: str) -> tuple[str, User]:
    user = session.execute(
        select(User).where(User.email == email.lower())
    ).scalar_one_or_none()
    if user is None or user.status != "active" or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    token = secrets.token_urlsafe(32)
    _tokens[token] = user.id
    return token, user


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )
    user_id = _tokens.get(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token"
        )
    user = session.get(User, user_id)
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active"
        )
    return user


def require_superuser(user: User = Depends(current_user)) -> User:
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Superuser required"
        )
    return user


def _resolve_member_role(
    session: Session, user: User, workspace_id: int
) -> tuple[Workspace, WorkspaceRole]:
    """Returns (workspace, effective_role). Raises 403/404 if access is denied."""
    workspace = session.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    member = session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    ).scalar_one_or_none()
    if member is not None:
        return workspace, member.role  # type: ignore[return-value]
    if user.is_superuser:
        # Superusers act with owner-equivalent access without an explicit membership.
        return workspace, "owner"
    raise HTTPException(status_code=403, detail="Not a member of this workspace")


def require_workspace_role(min_role: WorkspaceRole):
    """FastAPI dependency factory: ensures caller has at least min_role in {workspace_id}.

    Use as: `workspace: Workspace = Depends(require_workspace_role("admin"))`. The
    path must contain a {workspace_id} parameter.
    """
    threshold = _ROLE_RANK[min_role]

    def dependency(
        workspace_id: int = Path(...),
        user: User = Depends(current_user),
        session: Session = Depends(get_session),
    ) -> Workspace:
        workspace, role = _resolve_member_role(session, user, workspace_id)
        if _ROLE_RANK[role] < threshold:
            raise HTTPException(
                status_code=403,
                detail=f"Requires workspace role >= {min_role}; you have {role}",
            )
        return workspace

    return dependency
