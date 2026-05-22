"""Workspace CRUD and member management.

A workspace represents one of the agency's client tenants. The creating
user is automatically added as an owner; superusers can act with owner
privileges on any workspace without an explicit membership.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User, Workspace, WorkspaceMember
from app.schemas import (
    WorkspaceCreate,
    WorkspaceDetail,
    WorkspaceMemberAdd,
    WorkspaceMemberPublic,
    WorkspaceMemberUpdate,
    WorkspaceSummary,
    WorkspaceUpdate,
)
from app.services import auth_service

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    return _SLUG_RE.sub("-", name.lower()).strip("-") or "workspace"


def _unique_slug(session: Session, base: str) -> str:
    candidate = base
    n = 2
    while session.execute(select(Workspace).where(Workspace.slug == candidate)).first():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


@router.get("", response_model=list[WorkspaceSummary])
def list_workspaces(
    user: User = Depends(auth_service.current_user),
    session: Session = Depends(get_session),
) -> list[WorkspaceSummary]:
    rows = session.execute(
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.name)
    ).all()
    return [
        WorkspaceSummary(id=ws.id, slug=ws.slug, name=ws.name, role=role)
        for ws, role in rows
    ]


@router.post("", response_model=WorkspaceDetail, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    user: User = Depends(auth_service.current_user),
    session: Session = Depends(get_session),
) -> WorkspaceDetail:
    requested_slug = (payload.slug or _slugify(payload.name)).strip()
    if not requested_slug:
        requested_slug = "workspace"
    slug = _unique_slug(session, requested_slug)

    workspace = Workspace(
        name=payload.name.strip(),
        slug=slug,
        created_by_user_id=user.id,
    )
    session.add(workspace)
    session.flush()  # populate workspace.id
    session.add(
        WorkspaceMember(user_id=user.id, workspace_id=workspace.id, role="owner")
    )
    session.commit()
    session.refresh(workspace)
    return WorkspaceDetail.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceDetail)
def get_workspace(
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
) -> WorkspaceDetail:
    return WorkspaceDetail.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceDetail)
def update_workspace(
    payload: WorkspaceUpdate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> WorkspaceDetail:
    fields = payload.model_dump(exclude_unset=True)
    if "slug" in fields and fields["slug"]:
        slug = fields["slug"].strip()
        if slug != workspace.slug:
            if session.execute(select(Workspace).where(Workspace.slug == slug)).first():
                raise HTTPException(status_code=409, detail="Slug already taken")
        fields["slug"] = slug
    for key, value in fields.items():
        if value is not None:
            setattr(workspace, key, value)
    session.commit()
    session.refresh(workspace)
    return WorkspaceDetail.model_validate(workspace)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace: Workspace = Depends(auth_service.require_workspace_role("owner")),
    session: Session = Depends(get_session),
) -> None:
    session.delete(workspace)
    session.commit()


# ---------- Members ----------


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberPublic])
def list_members(
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> list[WorkspaceMemberPublic]:
    rows = session.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace.id)
        .order_by(WorkspaceMember.created_at)
    ).all()
    return [
        WorkspaceMemberPublic(
            id=member.id,
            user_id=member.user_id,
            role=member.role,
            created_at=member.created_at,
            user_email=user.email,
            user_name=user.name,
        )
        for member, user in rows
    ]


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberPublic,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    payload: WorkspaceMemberAdd,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> WorkspaceMemberPublic:
    target = session.get(User, payload.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    existing = session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == payload.user_id,
            WorkspaceMember.workspace_id == workspace.id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="User is already a member")
    member = WorkspaceMember(
        user_id=payload.user_id, workspace_id=workspace.id, role=payload.role
    )
    session.add(member)
    session.commit()
    session.refresh(member)
    return WorkspaceMemberPublic(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        created_at=member.created_at,
        user_email=target.email,
        user_name=target.name,
    )


@router.patch(
    "/{workspace_id}/members/{member_id}", response_model=WorkspaceMemberPublic
)
def update_member(
    member_id: int,
    payload: WorkspaceMemberUpdate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> WorkspaceMemberPublic:
    member = session.get(WorkspaceMember, member_id)
    if member is None or member.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Member not found")
    member.role = payload.role
    session.commit()
    session.refresh(member)
    target = session.get(User, member.user_id)
    return WorkspaceMemberPublic(
        id=member.id,
        user_id=member.user_id,
        role=member.role,
        created_at=member.created_at,
        user_email=target.email if target else "",
        user_name=target.name if target else "",
    )


@router.delete(
    "/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_member(
    member_id: int,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> None:
    member = session.get(WorkspaceMember, member_id)
    if member is None or member.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Member not found")
    # Don't allow removing the last owner; they'd lock everyone out.
    if member.role == "owner":
        owner_count = session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.role == "owner",
            )
        ).all()
        if len(owner_count) <= 1:
            raise HTTPException(
                status_code=400, detail="Cannot remove the last owner"
            )
    session.delete(member)
    session.commit()
