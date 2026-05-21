from fastapi import APIRouter

from app.services import store

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview() -> dict[str, int | str | dict[str, int]]:
    outcomes: dict[str, int] = {}
    visible_calls = [
        call
        for call in store.calls.values()
        if not store.is_internal_qa_record(call.id, call.contact_name, call.summary, " ".join(message.content for message in call.messages))
    ]
    visible_appointments = [
        appointment
        for appointment in store.appointments.values()
        if not store.is_internal_qa_record(appointment.contact_name, appointment.title, appointment.notes)
    ]
    visible_campaigns = [campaign for campaign in store.campaigns.values() if not store.is_internal_qa_record(campaign.name, campaign.prompt)]
    visible_contacts = [contact for contact in store.contacts.values() if not store.is_internal_qa_record(contact.name, contact.email, contact.source)]
    for call in visible_calls:
        outcomes[call.outcome] = outcomes.get(call.outcome, 0) + 1
    return {
        "total_calls": len(visible_calls),
        "appointments_booked": len(visible_appointments),
        "campaigns": len(visible_campaigns),
        "contacts": len(visible_contacts),
        "rag_questions_answered": sum(1 for call in visible_calls for message in call.messages if "FAQ" in message.content),
        "estimated_local_platform_cost": "$0",
        "top_outcomes": outcomes,
    }
