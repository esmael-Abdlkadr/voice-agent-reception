from fastapi import APIRouter, Depends, HTTPException, status

from app.models import UserCreate, UserPublic, UserUpdate
from app.services import auth_service, store

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(_user=Depends(auth_service.require_roles("platform_admin"))) -> list[UserPublic]:
    return [auth_service.public_user(user) for user in store.users.values()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, _user=Depends(auth_service.require_roles("platform_admin"))) -> UserPublic:
    return auth_service.public_user(auth_service.create_user(payload))


@router.get("/{user_id}")
def get_user(user_id: str, _user=Depends(auth_service.require_roles("platform_admin"))) -> UserPublic:
    if user_id not in store.users:
        raise HTTPException(status_code=404, detail="User not found")
    return auth_service.public_user(store.users[user_id])


@router.patch("/{user_id}")
def update_user(user_id: str, payload: UserUpdate, _user=Depends(auth_service.require_roles("platform_admin"))) -> UserPublic:
    if user_id not in store.users:
        raise HTTPException(status_code=404, detail="User not found")
    update = payload.model_dump(exclude_unset=True)
    if "role" in update:
        auth_service.assert_valid_role(update["role"])
        update["role"] = auth_service.normalize_role(update["role"])
    if "password" in update:
        update["password_hash"] = auth_service.hash_password(update.pop("password"))
    user = store.users[user_id].model_copy(update=update)
    store.users[user.id] = user
    return auth_service.public_user(user)
