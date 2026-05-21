from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models import User, UserCreate, UserPublic
from app.services import store

security = HTTPBearer(auto_error=False)
_tokens: dict[str, str] = {}
ROLE_ALIASES = {
    "admin": "platform_admin",
    "operator": "campaign_operator",
    "viewer": "analyst",
}
VALID_ROLES = {"platform_admin", "campaign_operator", "analyst"}


def hash_password(password: str) -> str:
    digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return f"sha256${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    return ROLE_ALIASES.get(normalized, normalized)


def assert_valid_role(role: str) -> None:
    if normalize_role(role) not in VALID_ROLES:
        supported = ", ".join(sorted(VALID_ROLES))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unsupported role. Use one of: {supported}")


def public_user(user: User) -> UserPublic:
    return UserPublic(id=user.id, email=user.email, name=user.name, role=normalize_role(user.role), status=user.status)


def create_user(payload: UserCreate) -> User:
    if any(existing.email.lower() == payload.email.lower() for existing in store.users.values()):
        raise HTTPException(status_code=409, detail="User email already exists")
    assert_valid_role(payload.role)
    user = User(
        id=store.next_id("user"),
        email=payload.email,
        name=payload.name,
        role=normalize_role(payload.role),
        password_hash=hash_password(payload.password),
        status=payload.status,
    )
    store.users[user.id] = user
    return user


def login(email: str, password: str) -> tuple[str, User]:
    for user in store.users.values():
        if user.email.lower() == email.lower() and user.status == "active" and verify_password(password, user.password_hash):
            token = secrets.token_urlsafe(32)
            _tokens[token] = user.id
            return token, user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    user_id = _tokens.get(credentials.credentials)
    if user_id is None or user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")
    user = store.users[user_id]
    canonical_role = normalize_role(user.role)
    if user.role != canonical_role:
        user = user.model_copy(update={"role": canonical_role})
        store.users[user.id] = user
    return user


def require_roles(*roles: str):
    allowed_roles = {normalize_role(role) for role in roles}

    def dependency(user: User = Depends(current_user)) -> User:
        if normalize_role(user.role) not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency
