from fastapi import APIRouter, Depends, HTTPException, status

from app.models import AgentProfile, AgentProfileCreate, AgentProfileUpdate
from app.services import auth_service, store

router = APIRouter(prefix="/agent-profiles", tags=["agent profiles"])


@router.get("")
def list_profiles() -> list[AgentProfile]:
    return list(store.agent_profiles.values())


@router.post("", status_code=status.HTTP_201_CREATED)
def create_profile(payload: AgentProfileCreate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> AgentProfile:
    profile = AgentProfile(id=store.next_id("profile"), **payload.model_dump())
    store.agent_profiles[profile.id] = profile
    return profile


@router.get("/{profile_id}")
def get_profile(profile_id: str) -> AgentProfile:
    if profile_id not in store.agent_profiles:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    return store.agent_profiles[profile_id]


@router.patch("/{profile_id}")
def update_profile(profile_id: str, payload: AgentProfileUpdate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> AgentProfile:
    if profile_id not in store.agent_profiles:
        raise HTTPException(status_code=404, detail="Agent profile not found")
    profile = store.agent_profiles[profile_id].model_copy(update=payload.model_dump(exclude_unset=True))
    store.agent_profiles[profile.id] = profile
    return profile
