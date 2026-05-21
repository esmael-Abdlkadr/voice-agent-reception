from fastapi import APIRouter, Depends

from app.models import LoginRequest, TokenResponse, UserPublic
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest) -> TokenResponse:
    token, user = auth_service.login(payload.email, payload.password)
    return TokenResponse(access_token=token, user=auth_service.public_user(user))


@router.get("/me")
def me(user=Depends(auth_service.current_user)) -> UserPublic:
    return auth_service.public_user(user)
