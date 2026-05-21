from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.models import Contact, ContactCreate, ContactUpdate
from app.services import auth_service, store

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("")
def list_contacts() -> list[Contact]:
    return list(store.contacts.values())


@router.post("", status_code=status.HTTP_201_CREATED)
def create_contact(payload: ContactCreate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> Contact:
    contact = Contact(id=store.next_id("contact"), **payload.model_dump())
    store.contacts[contact.id] = contact
    return contact


@router.get("/{contact_id}")
def get_contact(contact_id: str) -> Contact:
    if contact_id not in store.contacts:
        raise HTTPException(status_code=404, detail="Contact not found")
    return store.contacts[contact_id]


@router.patch("/{contact_id}")
def update_contact(contact_id: str, payload: ContactUpdate, _user=Depends(auth_service.require_roles("platform_admin", "campaign_operator"))) -> Contact:
    if contact_id not in store.contacts:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact = store.contacts[contact_id].model_copy(update=payload.model_dump(exclude_unset=True))
    store.contacts[contact.id] = contact
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: str, _user=Depends(auth_service.require_roles("platform_admin"))) -> Response:
    if contact_id not in store.contacts:
        raise HTTPException(status_code=404, detail="Contact not found")
    del store.contacts[contact_id]
    return Response(status_code=status.HTTP_204_NO_CONTENT)
