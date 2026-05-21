from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.models import Appointment, AppointmentCreate, AppointmentUpdate
from app.services import auth_service, store

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("")
def list_appointments() -> list[Appointment]:
    return list(store.appointments.values())


@router.post("", status_code=status.HTTP_201_CREATED)
def create_appointment(payload: AppointmentCreate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> Appointment:
    appointment = Appointment(id=store.next_id("appointment"), **payload.model_dump())
    store.appointments[appointment.id] = appointment
    return appointment


@router.get("/{appointment_id}")
def get_appointment(appointment_id: str) -> Appointment:
    if appointment_id not in store.appointments:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return store.appointments[appointment_id]


@router.patch("/{appointment_id}")
def update_appointment(appointment_id: str, payload: AppointmentUpdate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> Appointment:
    if appointment_id not in store.appointments:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appointment = store.appointments[appointment_id].model_copy(update=payload.model_dump(exclude_unset=True))
    store.appointments[appointment.id] = appointment
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(appointment_id: str, _user=Depends(auth_service.require_roles("platform_admin"))) -> Response:
    if appointment_id not in store.appointments:
        raise HTTPException(status_code=404, detail="Appointment not found")
    del store.appointments[appointment_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
