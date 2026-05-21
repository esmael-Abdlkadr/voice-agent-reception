from fastapi import APIRouter, Depends

from app.models import RuntimeSettings
from app.services import auth_service, runtime_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/runtime")
def get_runtime() -> RuntimeSettings:
    return runtime_service.get_runtime()


@router.put("/runtime")
def update_runtime(payload: RuntimeSettings, _user=Depends(auth_service.require_roles("platform_admin"))) -> RuntimeSettings:
    return runtime_service.update_runtime(payload)
