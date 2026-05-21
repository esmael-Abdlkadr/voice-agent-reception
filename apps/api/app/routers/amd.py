from app.models import AmdAnalysisRequest, AmdSettings
from app.services import auth_service
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/amd", tags=["answer machine detection"])

_settings = AmdSettings()


@router.get("/settings")
def get_settings() -> AmdSettings:
    return _settings


@router.put("/settings")
def update_settings(payload: AmdSettings, _user=Depends(auth_service.require_roles("platform_admin"))) -> AmdSettings:
    global _settings
    _settings = payload
    return _settings


@router.post("/analyze")
def analyze(payload: AmdAnalysisRequest, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> dict[str, float | str]:
    text = payload.greeting_text.lower()
    voicemail_markers = ["leave a message", "after the tone", "not available", "mailbox", "voicemail"]
    is_voicemail = payload.audio_duration_seconds >= _settings.detection_window_seconds or any(marker in text for marker in voicemail_markers)
    confidence = _settings.sensitivity if is_voicemail else max(0.5, 1 - _settings.sensitivity / 2)
    return {"result": "voicemail" if is_voicemail else "live_person", "confidence": round(confidence, 2)}
