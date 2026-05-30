"""Hotel reservations (lightweight).

The voice agent records a reservation REQUEST during a call — dates, room
type, party size, guest. There's no live room inventory in V1; staff confirm
requests from the dashboard. The worker uses the service key (which passes
the viewer dependency) to create reservations on a call.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Reservation, User, Workspace
from app.schemas import ReservationCreate, ReservationPublic, ReservationUpdate
from app.services import auth_service

router = APIRouter(prefix="/workspaces/{workspace_id}/reservations", tags=["reservations"])


@router.get("/lookup", response_model=list[ReservationPublic])
def lookup_reservations(
    name: str | None = Query(default=None, description="Guest name (case-insensitive substring)"),
    phone: str | None = Query(default=None, description="Guest phone (exact match)"),
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    session: Session = Depends(get_session),
) -> list[ReservationPublic]:
    """Find a guest's reservations by name and/or phone. The voice agent uses
    this to confirm whether a caller's reservation exists. Returns [] if no
    search terms are given (so we never dump the whole list)."""
    if not name and not phone:
        return []
    stmt = select(Reservation).where(Reservation.workspace_id == workspace.id)
    if phone:
        stmt = stmt.where(Reservation.guest_phone == phone)
    if name:
        stmt = stmt.where(Reservation.guest_name.ilike(f"%{name.strip()}%"))
    stmt = stmt.order_by(Reservation.created_at.desc()).limit(20)
    rows = session.execute(stmt).scalars().all()
    return [ReservationPublic.model_validate(r) for r in rows]


@router.get("", response_model=list[ReservationPublic])
def list_reservations(
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    viewer: User = Depends(auth_service.current_user),
    session: Session = Depends(get_session),
    upcoming_only: bool = Query(default=False),
) -> list[ReservationPublic]:
    stmt = select(Reservation).where(Reservation.workspace_id == workspace.id)
    if not auth_service.is_workspace_manager(session, viewer, workspace.id):
        stmt = stmt.where(Reservation.owner_user_id == viewer.id)
    if upcoming_only:
        stmt = stmt.where(Reservation.check_in >= datetime.now(timezone.utc).date())
    stmt = stmt.order_by(Reservation.check_in).limit(500)
    rows = session.execute(stmt).scalars().all()
    return [ReservationPublic.model_validate(r) for r in rows]


@router.post("", response_model=ReservationPublic, status_code=status.HTTP_201_CREATED)
def create_reservation(
    payload: ReservationCreate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("viewer")),
    caller: User | None = Depends(auth_service.optional_user),
    session: Session = Depends(get_session),
) -> ReservationPublic:
    if payload.check_out <= payload.check_in:
        raise HTTPException(
            status_code=422, detail="check_out must be after check_in (at least one night)"
        )
    reservation = Reservation(
        workspace_id=workspace.id,
        owner_user_id=caller.id if caller else None,
        guest_name=payload.guest_name,
        guest_phone=payload.guest_phone,
        check_in=payload.check_in,
        check_out=payload.check_out,
        room_type=payload.room_type,
        num_guests=payload.num_guests,
        notes=payload.notes,
        status="requested",
        call_id=payload.call_id,
    )
    session.add(reservation)
    session.commit()
    session.refresh(reservation)
    return ReservationPublic.model_validate(reservation)


@router.patch("/{reservation_id}", response_model=ReservationPublic)
def update_reservation(
    reservation_id: int,
    payload: ReservationUpdate,
    workspace: Workspace = Depends(auth_service.require_workspace_role("admin")),
    session: Session = Depends(get_session),
) -> ReservationPublic:
    res = session.get(Reservation, reservation_id)
    if res is None or res.workspace_id != workspace.id:
        raise HTTPException(status_code=404, detail="Reservation not found")
    fields = payload.model_dump(exclude_unset=True)
    for key, value in fields.items():
        if value is not None:
            setattr(res, key, value)
    session.commit()
    session.refresh(res)
    return ReservationPublic.model_validate(res)
