from fastapi import APIRouter, Depends, HTTPException, status

from app.models import Recording, RecordingCreate
from app.services import auth_service, store

router = APIRouter(prefix="/recordings", tags=["recordings"])


@router.get("")
def list_recordings() -> list[Recording]:
    return list(store.recordings.values())


@router.post("", status_code=status.HTTP_201_CREATED)
def create_recording(payload: RecordingCreate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> Recording:
    if payload.call_id not in store.calls:
        raise HTTPException(status_code=404, detail="Call not found")
    recording = Recording(id=store.next_id("recording"), **payload.model_dump())
    store.recordings[recording.id] = recording
    return recording


@router.get("/{recording_id}")
def get_recording(recording_id: str) -> Recording:
    if recording_id not in store.recordings:
        raise HTTPException(status_code=404, detail="Recording not found")
    return store.recordings[recording_id]
