from __future__ import annotations

import re

from app.models import AgentMessageCreate, Appointment, CallSession, Contact
from app.services import llm_service, store


def create_session(direction: str, contact_id: str | None = None, campaign_id: str | None = None) -> CallSession:
    contact = store.contacts.get(contact_id or "")
    session = CallSession(
        id=store.next_id("call"),
        contact_id=contact.id if contact else None,
        contact_name=contact.name if contact else "Unknown caller",
        campaign_id=campaign_id,
        direction=direction,
        started_at=store.now_iso(),
    )
    store.calls[session.id] = session
    return session


def handle_message(
    payload: AgentMessageCreate,
    appointment_status: str = "booked",
    booking_outcome: str = "appointment_booked",
    complete_on_booking: bool = True,
) -> dict:
    session = store.calls[payload.session_id]
    store.add_call_message(session, "user", payload.message)

    contact_name = _extract_name(payload.message) or session.contact_name
    if contact_name == "Unknown caller":
        contact_name = "New caller"

    contact = _find_or_create_contact(contact_name, payload.message)
    session.contact_id = contact.id
    session.contact_name = contact.name

    context = search_knowledge(payload.message)
    reply, llm_meta = llm_service.generate_inbound_reply(session, contact, payload.message, context)

    appointment = None
    if _looks_like_booking_request(payload.message):
        appointment = Appointment(
            id=store.next_id("appointment"),
            contact_id=contact.id,
            contact_name=contact.name,
            title="Dental appointment",
            starts_at=_slot_from_message(payload.message),
            status=appointment_status,
            notes="Booked by Ava after confirming the caller's preferred time.",
        )
        store.appointments[appointment.id] = appointment
        session.outcome = booking_outcome
        if complete_on_booking:
            session.status = "completed"
            session.ended_at = store.now_iso()
        session.summary = llm_service.summarize_call(contact.name, payload.message, reply, booking_outcome)
    else:
        session.outcome = "answered"
        session.summary = llm_service.summarize_call(contact.name, payload.message, reply, "answered")

    store.add_call_message(session, "assistant", reply)
    return {
        "reply": reply,
        "session": session,
        "appointment": appointment,
        "outcome": session.outcome,
        "knowledge": context[:2],
        "llm": llm_meta,
    }


def search_knowledge(query: str) -> list[dict]:
    terms = {term.lower() for term in re.findall(r"[a-zA-Z]{3,}", query)}
    results: list[dict] = []
    for doc in store.knowledge_documents.values():
        haystack = f"{doc.title} {doc.content}".lower()
        matched_terms = sorted(term for term in terms if term in haystack)
        score = len(matched_terms)
        if score:
            results.append({"id": doc.id, "title": doc.title, "content": doc.content, "score": score, "matched_terms": matched_terms})
    return sorted(results, key=lambda item: item["score"], reverse=True)


def simulate_campaign(campaign_id: str) -> dict:
    campaign = store.campaigns[campaign_id]
    campaign.status = "completed"
    store.save_campaign(campaign)
    outcomes: list[str] = []
    for index, contact in enumerate(store.contacts.values()):
        session = create_session("outbound", contact_id=contact.id, campaign_id=campaign.id)
        outcome = "appointment_booked" if index == 0 else "callback_requested"
        session.outcome = outcome
        session.status = "completed"
        session.ended_at = store.now_iso()
        assistant_line, user_line = llm_service.generate_campaign_lines(contact.name, campaign.prompt)
        session.summary = llm_service.summarize_call(contact.name, user_line, assistant_line, outcome)
        store.add_call_message(session, "assistant", assistant_line)
        store.add_call_message(session, "user", user_line)
        outcomes.append(outcome)
        if outcome == "appointment_booked":
            appointment = Appointment(
                id=store.next_id("appointment"),
                contact_id=contact.id,
                contact_name=contact.name,
                title="Whitening consultation",
                starts_at="Friday 10:00 AM",
                status="booked",
                notes="Qualified through the outbound campaign workflow.",
            )
            store.appointments[appointment.id] = appointment
    return {"campaign_id": campaign.id, "created_calls": len(outcomes), "outcomes": outcomes}


def _extract_name(message: str) -> str | None:
    match = re.search(r"(?:i am|i'm|this is)\s+([A-Z][a-zA-Z]+)", message, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).title()


def _find_or_create_contact(name: str, message: str) -> Contact:
    for contact in store.contacts.values():
        if contact.name.lower() == name.lower():
            return contact
    phone_match = re.search(r"(\d{3}[-.\s]?\d{4})", message)
    contact = Contact(
        id=store.next_id("contact"),
        name=name,
        phone=phone_match.group(1) if phone_match else "",
        email="",
        company="BrightCare Dental",
        source="agent",
    )
    store.contacts[contact.id] = contact
    return contact


def _looks_like_booking_request(message: str) -> bool:
    lowered = message.lower()
    return any(word in lowered for word in ["appointment", "cleaning", "whitening", "book", "schedule", "consult"])


def _slot_from_message(message: str) -> str:
    lowered = message.lower()
    for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
        if day in lowered:
            label = day.title()
            time = "10:00 AM" if "morning" in lowered else "2:00 PM"
            return f"{label} {time}"
    return "Friday 10:00 AM"
