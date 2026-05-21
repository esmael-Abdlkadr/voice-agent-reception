from fastapi import APIRouter, Depends

from app.models import OrchestrationConfig
from app.services import auth_service

router = APIRouter(prefix="/orchestration", tags=["orchestration"])

_config = OrchestrationConfig()


@router.get("/config")
def get_config() -> OrchestrationConfig:
    return _config


@router.put("/config")
def update_config(payload: OrchestrationConfig, _user=Depends(auth_service.require_roles("platform_admin"))) -> OrchestrationConfig:
    global _config
    _config = payload
    return _config
