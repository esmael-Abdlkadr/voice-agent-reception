"""User CRUD (superuser-only). Workspace-scoped permissions land later."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.schemas import UserCreate, UserPublic, UserUpdate
from app.services import auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserPublic])
def list_users(
    _superuser: User = Depends(auth_service.require_superuser),
    session: Session = Depends(get_session),
) -> list[UserPublic]:
    users = session.execute(select(User).order_by(User.created_at)).scalars().all()
    return [UserPublic.model_validate(u) for u in users]


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    _superuser: User = Depends(auth_service.require_superuser),
    session: Session = Depends(get_session),
) -> UserPublic:
    if session.execute(select(User).where(User.email == payload.email.lower())).first():
        raise HTTPException(status_code=409, detail="User email already exists")
    user = User(
        email=payload.email.lower(),
        name=payload.name,
        password_hash=auth_service.hash_password(payload.password),
        is_superuser=payload.is_superuser,
        status="active",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserPublic.model_validate(user)


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    payload: UserUpdate,
    _superuser: User = Depends(auth_service.require_superuser),
    session: Session = Depends(get_session),
) -> UserPublic:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    fields = payload.model_dump(exclude_unset=True)
    if "password" in fields:
        user.password_hash = auth_service.hash_password(fields.pop("password"))
    for key, value in fields.items():
        setattr(user, key, value)
    session.commit()
    session.refresh(user)
    return UserPublic.model_validate(user)
