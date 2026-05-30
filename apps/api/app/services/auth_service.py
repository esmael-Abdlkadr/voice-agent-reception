"""Authentication and workspace-scoped authorization helpers.

Sessions are stateless JWTs (HS256) signed with settings.jwt_secret, so they
survive API restarts and work across multiple processes — no server-side
session store. The token carries the user id in `sub` and an expiry in `exp`.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.models import User, Workspace, WorkspaceMember

WorkspaceRole = Literal["owner", "admin", "viewer"]
_ROLE_RANK = {"viewer": 1, "admin": 2, "owner": 3}
_JWT_ALG = "HS256"

_security = HTTPBearer(auto_error=False)


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=settings.jwt_expire_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALG)


def user_id_from_token(token: str) -> Optional[int]:
    """Decode + verify a session JWT, returning the user id or None."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALG])
        return int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def is_service_credential(credentials: HTTPAuthorizationCredentials | None) -> bool:
    """True if the bearer token is the shared service key (used by the voice
    worker on phone calls, where no operator session exists)."""
    key = settings.service_api_key
    return bool(
        key
        and credentials is not None
        and credentials.scheme.lower() == "bearer"
        and secrets.compare_digest(credentials.credentials, key)
    )


def require_service_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> None:
    """Dependency that only allows the service key. For internal endpoints."""
    if not is_service_credential(credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Service key required"
        )


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
    return create_access_token(user.id), user


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )
    user_id = user_id_from_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
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


def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
    session: Session = Depends(get_session),
) -> User | None:
    """Resolve the calling user from a bearer JWT, or None for the service key
    / anonymous. Used to attribute ownership of records the worker creates:
    browser calls carry the operator's JWT (→ that user), phone calls use the
    service key (→ None, i.e. workspace-level)."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    if is_service_credential(credentials):
        return None
    user_id = user_id_from_token(credentials.credentials)
    if user_id is None:
        return None
    return session.get(User, user_id)


def is_workspace_manager(session: Session, user: User, workspace_id: int) -> bool:
    """True if the user can see ALL of a workspace's records (owner/admin or
    superuser). Regular members only see their own."""
    if user.is_superuser:
        return True
    member = session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    ).scalar_one_or_none()
    return member is not None and member.role in ("owner", "admin")


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
        credentials: HTTPAuthorizationCredentials | None = Depends(_security),
        session: Session = Depends(get_session),
    ) -> Workspace:
        # The voice worker authenticates with the service key on phone calls;
        # it acts as the system and may reach any workspace.
        if is_service_credential(credentials):
            workspace = session.get(Workspace, workspace_id)
            if workspace is None:
                raise HTTPException(status_code=404, detail="Workspace not found")
            return workspace

        user = current_user(credentials=credentials, session=session)
        workspace, role = _resolve_member_role(session, user, workspace_id)
        if _ROLE_RANK[role] < threshold:
            raise HTTPException(
                status_code=403,
                detail=f"Requires workspace role >= {min_role}; you have {role}",
            )
        return workspace

    return dependency
