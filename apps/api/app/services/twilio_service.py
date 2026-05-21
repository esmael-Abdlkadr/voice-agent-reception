from __future__ import annotations

import base64
import hashlib
import hmac
import os
from html import escape
from urllib.parse import parse_qs

from fastapi import HTTPException, Request

from app.models import CallSession, Contact, TwilioSetupStatus
from app.services import store

_YES = {"1", "true", "yes", "on"}


async def parse_webhook_form(request: Request) -> dict[str, str]:
    raw_body = await request.body()
    parsed = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def validate_webhook_or_raise(request: Request, params: dict[str, str]) -> None:
    if not validate_webhooks_enabled():
        return
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    signature = request.headers.get("X-Twilio-Signature", "")
    if not auth_token or not signature:
        raise HTTPException(status_code=403, detail="Twilio webhook signature is required")

    expected = _compute_signature(_request_url(request), params, auth_token)
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Invalid Twilio webhook signature")


def setup_status() -> TwilioSetupStatus:
    base_url = public_base_url()
    return TwilioSetupStatus(
        account_sid_configured=bool(os.getenv("TWILIO_ACCOUNT_SID", "").strip()),
        auth_token_configured=bool(os.getenv("TWILIO_AUTH_TOKEN", "").strip()),
        phone_number_configured=bool(os.getenv("TWILIO_PHONE_NUMBER", "").strip()),
        public_webhook_base_url=base_url,
        validate_webhooks=validate_webhooks_enabled(),
        inbound_webhook_url=f"{base_url}/twilio/voice/inbound" if base_url else "/twilio/voice/inbound",
        gather_webhook_url=f"{base_url}/twilio/voice/gather" if base_url else "/twilio/voice/gather",
        status_callback_url=f"{base_url}/twilio/voice/status" if base_url else "/twilio/voice/status",
        recording_callback_url=f"{base_url}/twilio/voice/recording" if base_url else "/twilio/voice/recording",
    )


def public_base_url() -> str:
    return os.getenv("PUBLIC_WEBHOOK_BASE_URL", "").strip().rstrip("/")


def validate_webhooks_enabled() -> bool:
    return os.getenv("TWILIO_VALIDATE_WEBHOOKS", "false").strip().lower() in _YES


def find_session_by_call_sid(call_sid: str) -> CallSession | None:
    for call in store.calls.values():
        if call.external_call_id == call_sid:
            return call
    return None


def find_or_create_inbound_session(params: dict[str, str]) -> CallSession:
    call_sid = params.get("CallSid", "")
    existing = find_session_by_call_sid(call_sid)
    if existing:
        existing.provider_status = params.get("CallStatus", existing.provider_status)
        existing.last_webhook_at = store.now_iso()
        store.save_call(existing)
        return existing

    caller_number = params.get("From", "")
    called_number = params.get("To", "")
    contact = _find_or_create_contact_for_number(caller_number)
    session = CallSession(
        id=store.next_id("call"),
        contact_id=contact.id,
        contact_name=contact.name,
        direction="inbound",
        status="active",
        outcome="in_progress",
        provider="twilio",
        external_call_id=call_sid,
        caller_number=caller_number,
        called_number=called_number,
        provider_status=params.get("CallStatus", "ringing"),
        started_at=store.now_iso(),
        last_webhook_at=store.now_iso(),
    )
    store.calls[session.id] = session
    return session


def twiml_response(body: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>'


def gather_twiml(prompt: str, action: str | None = None) -> str:
    action_url = action or _webhook_path("/twilio/voice/gather")
    return twiml_response(
        (
            f'<Gather input="speech dtmf" action="{escape(action_url)}" method="POST" '
            'speechTimeout="auto" timeout="5" language="en-US">'
            f"<Say voice=\"alice\">{escape(prompt)}</Say>"
            "</Gather>"
            "<Say voice=\"alice\">I did not hear anything. Please call us again when you are ready.</Say>"
        )
    )


def say_and_gather_twiml(message: str) -> str:
    return gather_twiml(message)


def hangup_twiml(message: str) -> str:
    return twiml_response(f"<Say voice=\"alice\">{escape(message)}</Say><Hangup />")


def _find_or_create_contact_for_number(phone: str):
    normalized = _digits(phone)
    for contact in store.contacts.values():
        if _digits(contact.phone) and _digits(contact.phone) == normalized:
            return contact
    display = phone or "Phone caller"
    new_contact = Contact(
        id=store.next_id("contact"),
        name=f"Caller {display[-4:]}" if normalized else "Phone caller",
        phone=phone,
        email="",
        company="BrightCare Dental",
        source="twilio",
    )
    store.contacts[new_contact.id] = new_contact
    return new_contact


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _request_url(request: Request) -> str:
    configured_base = public_base_url()
    if configured_base:
        return f"{configured_base}{request.url.path}"
    return str(request.url)


def _webhook_path(path: str) -> str:
    configured_base = public_base_url()
    return f"{configured_base}{path}" if configured_base else path


def _compute_signature(url: str, params: dict[str, str], auth_token: str) -> str:
    signed = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(auth_token.encode("utf-8"), signed.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")
