from fastapi import APIRouter, Depends, HTTPException

from app.models import CallSession, CallSessionUpdate
from app.services import auth_service, store

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("")
def list_calls() -> list[CallSession]:
    return list(store.calls.values())


@router.get("/{call_id}")
def get_call(call_id: str) -> CallSession:
    if call_id not in store.calls:
        raise HTTPException(status_code=404, detail="Call not found")
    return store.calls[call_id]


@router.patch("/{call_id}")
def update_call(call_id: str, payload: CallSessionUpdate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> CallSession:
    if call_id not in store.calls:
        raise HTTPException(status_code=404, detail="Call not found")
    call = store.calls[call_id].model_copy(update=payload.model_dump(exclude_unset=True))
    store.calls[call.id] = call
    return call
