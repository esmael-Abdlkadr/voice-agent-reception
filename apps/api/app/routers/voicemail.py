from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.models import VoicemailTemplate, VoicemailTemplateCreate, VoicemailTemplateUpdate
from app.services import auth_service, store

router = APIRouter(prefix="/voicemail", tags=["voicemail"])


@router.get("/templates")
def list_templates() -> list[VoicemailTemplate]:
    return list(store.voicemail_templates.values())


@router.post("/templates", status_code=status.HTTP_201_CREATED)
def create_template(payload: VoicemailTemplateCreate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> VoicemailTemplate:
    template = VoicemailTemplate(id=store.next_id("voicemail"), **payload.model_dump())
    store.voicemail_templates[template.id] = template
    return template


@router.get("/templates/{template_id}")
def get_template(template_id: str) -> VoicemailTemplate:
    if template_id not in store.voicemail_templates:
        raise HTTPException(status_code=404, detail="Voicemail template not found")
    return store.voicemail_templates[template_id]


@router.patch("/templates/{template_id}")
def update_template(template_id: str, payload: VoicemailTemplateUpdate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> VoicemailTemplate:
    if template_id not in store.voicemail_templates:
        raise HTTPException(status_code=404, detail="Voicemail template not found")
    template = store.voicemail_templates[template_id].model_copy(update=payload.model_dump(exclude_unset=True))
    store.voicemail_templates[template.id] = template
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: str, _user=Depends(auth_service.require_roles("platform_admin"))) -> Response:
    if template_id not in store.voicemail_templates:
        raise HTTPException(status_code=404, detail="Voicemail template not found")
    del store.voicemail_templates[template_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
