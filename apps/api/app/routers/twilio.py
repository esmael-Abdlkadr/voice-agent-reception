from fastapi import APIRouter, HTTPException, Request, Response

from app.models import AgentMessageCreate, TwilioSetupStatus
from app.services import agent_service, store, twilio_service

router = APIRouter(prefix="/twilio", tags=["twilio"])


def _xml(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


@router.get("/setup")
def setup_status() -> TwilioSetupStatus:
    return twilio_service.setup_status()


@router.post("/voice/inbound")
async def inbound_voice(request: Request) -> Response:
    params = await twilio_service.parse_webhook_form(request)
    twilio_service.validate_webhook_or_raise(request, params)
    session = twilio_service.find_or_create_inbound_session(params)
    prompt = (
        "Thanks for calling BrightCare Dental. This is Ava, the AI receptionist. "
        "How can I help with appointments, pricing, hours, or follow up today?"
    )
    if not session.messages:
        store.add_call_message(session, "assistant", prompt)
    return _xml(twilio_service.gather_twiml(prompt))


@router.post("/voice/gather")
async def gather_voice(request: Request) -> Response:
    params = await twilio_service.parse_webhook_form(request)
    twilio_service.validate_webhook_or_raise(request, params)
    session = twilio_service.find_or_create_inbound_session(params)
    caller_text = (params.get("SpeechResult") or params.get("Digits") or "").strip()

    if not caller_text:
        return _xml(twilio_service.gather_twiml("I did not catch that. Please tell me how I can help today."))

    if caller_text.lower() in {"bye", "goodbye", "hang up", "end call"}:
        session.status = "completed"
        session.outcome = "answered" if session.outcome == "in_progress" else session.outcome
        session.ended_at = store.now_iso()
        store.save_call(session)
        return _xml(twilio_service.hangup_twiml("Thanks for calling BrightCare Dental. Goodbye."))

    result = agent_service.handle_message(
        AgentMessageCreate(session_id=session.id, message=caller_text),
        appointment_status="requested",
        booking_outcome="appointment_requested",
        complete_on_booking=False,
    )
    updated_session = result["session"]
    updated_session.provider = "twilio"
    updated_session.external_call_id = params.get("CallSid", updated_session.external_call_id)
    updated_session.caller_number = params.get("From", updated_session.caller_number)
    updated_session.called_number = params.get("To", updated_session.called_number)
    updated_session.provider_status = params.get("CallStatus", updated_session.provider_status)
    updated_session.last_webhook_at = store.now_iso()
    store.save_call(updated_session)

    appointment = result.get("appointment")
    if appointment:
        appointment.notes = "Requested by phone call. Staff should confirm the final appointment time."
        store.appointments[appointment.id] = appointment

    reply = result["reply"]
    if appointment:
        reply = (
            "I captured your appointment request and sent it to the BrightCare Dental team for confirmation. "
            "Is there anything else I can help with?"
        )
    return _xml(twilio_service.say_and_gather_twiml(reply))


@router.post("/voice/status")
async def voice_status(request: Request) -> dict[str, str | int]:
    params = await twilio_service.parse_webhook_form(request)
    twilio_service.validate_webhook_or_raise(request, params)
    session = twilio_service.find_session_by_call_sid(params.get("CallSid", ""))
    if not session:
        raise HTTPException(status_code=404, detail="Twilio call session not found")

    provider_status = params.get("CallStatus", "")
    session.provider_status = provider_status
    session.last_webhook_at = store.now_iso()
    if params.get("CallDuration", "").isdigit():
        session.duration_seconds = int(params["CallDuration"])
    if provider_status == "completed":
        session.status = "completed"
        session.ended_at = store.now_iso()
        if session.outcome == "in_progress":
            session.outcome = "answered"
    store.save_call(session)
    return {"status": "ok", "duration_seconds": session.duration_seconds}


@router.post("/voice/recording")
async def recording_status(request: Request) -> dict[str, str]:
    params = await twilio_service.parse_webhook_form(request)
    twilio_service.validate_webhook_or_raise(request, params)
    return {"status": "received"}
