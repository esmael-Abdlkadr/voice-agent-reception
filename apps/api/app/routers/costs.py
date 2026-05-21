from fastapi import APIRouter, Depends

from app.models import CostEstimateRequest
from app.services import auth_service

router = APIRouter(prefix="/costs", tags=["costs"])


@router.post("/estimate")
def estimate(payload: CostEstimateRequest, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> dict[str, float]:
    total_minutes = payload.daily_calls * payload.average_call_minutes
    live_minutes = total_minutes * payload.live_answer_rate
    voicemail_minutes = total_minutes - live_minutes
    sip_cost = total_minutes * payload.sip_cost_per_minute
    ai_cost = live_minutes * payload.ai_cost_per_live_minute
    voicemail_cost = voicemail_minutes * payload.voicemail_cost_per_minute
    return {
        "total_daily_minutes": round(total_minutes, 2),
        "live_daily_minutes": round(live_minutes, 2),
        "voicemail_daily_minutes": round(voicemail_minutes, 2),
        "estimated_daily_cost": round(sip_cost + ai_cost + voicemail_cost, 2),
    }
