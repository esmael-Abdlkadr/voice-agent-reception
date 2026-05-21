from fastapi import APIRouter, Depends, HTTPException, status

from app.models import CallSession, OutboundCallRequest, SipTrunk, SipTrunkCreate, SipTrunkUpdate
from app.services import auth_service, store

router = APIRouter(prefix="/sip", tags=["sip"])


@router.get("/trunks")
def list_trunks() -> list[SipTrunk]:
    return list(store.sip_trunks.values())


@router.post("/trunks", status_code=status.HTTP_201_CREATED)
def create_trunk(payload: SipTrunkCreate, _user=Depends(auth_service.require_roles("platform_admin"))) -> SipTrunk:
    trunk = SipTrunk(id=store.next_id("sip"), **payload.model_dump())
    store.sip_trunks[trunk.id] = trunk
    return trunk


@router.get("/trunks/{trunk_id}")
def get_trunk(trunk_id: str) -> SipTrunk:
    if trunk_id not in store.sip_trunks:
        raise HTTPException(status_code=404, detail="SIP trunk not found")
    return store.sip_trunks[trunk_id]


@router.patch("/trunks/{trunk_id}")
def update_trunk(trunk_id: str, payload: SipTrunkUpdate, _user=Depends(auth_service.require_roles("platform_admin"))) -> SipTrunk:
    if trunk_id not in store.sip_trunks:
        raise HTTPException(status_code=404, detail="SIP trunk not found")
    trunk = store.sip_trunks[trunk_id].model_copy(update=payload.model_dump(exclude_unset=True))
    store.sip_trunks[trunk.id] = trunk
    return trunk


@router.post("/outbound-call", status_code=status.HTTP_201_CREATED)
def create_outbound_call(payload: OutboundCallRequest, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> CallSession:
    if payload.trunk_id not in store.sip_trunks:
        raise HTTPException(status_code=404, detail="SIP trunk not found")
    if payload.contact_id not in store.contacts:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact = store.contacts[payload.contact_id]
    call = CallSession(
        id=store.next_id("call"),
        contact_id=contact.id,
        contact_name=contact.name,
        campaign_id=payload.campaign_id,
        direction="outbound",
        status="queued",
        outcome="queued",
        summary=f"Queued outbound SIP call through trunk {payload.trunk_id}.",
        started_at=store.now_iso(),
    )
    store.calls[call.id] = call
    return call
