from fastapi import APIRouter, Depends

from app.models import LlmChatRequest, LlmChatResponse, LlmHealthResponse, LlmModelInfo, LlmModelsResponse
from app.services import auth_service, llm_service

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/health")
def llm_health(_user=Depends(auth_service.require_roles("platform_admin", "campaign_operator", "analyst"))) -> LlmHealthResponse:
    return LlmHealthResponse(**llm_service.llm_health())


@router.get("/models")
def list_models(_user=Depends(auth_service.require_roles("platform_admin", "campaign_operator", "analyst"))) -> LlmModelsResponse:
    return LlmModelsResponse(provider="groq", models=[LlmModelInfo(**item) for item in llm_service.list_models()])


@router.post("/chat")
def chat(payload: LlmChatRequest, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> LlmChatResponse:
    reply, llm_meta = llm_service.direct_chat(payload.message, payload.system_prompt, payload.model)
    return LlmChatResponse(reply=reply, llm=llm_meta)
