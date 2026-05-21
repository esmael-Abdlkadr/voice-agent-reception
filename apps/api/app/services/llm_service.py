from __future__ import annotations

import os
import re
from typing import Any

import httpx

from app.models import CallSession, Contact
from app.services import runtime_service

_YES = {"1", "true", "yes", "on"}


def generate_inbound_reply(session: CallSession, contact: Contact, user_message: str, context: list[dict[str, Any]]) -> tuple[str, dict[str, str]]:
    runtime = runtime_service.get_runtime()
    if _force_deterministic(runtime.llm_provider):
        return _fallback_reply(contact.name, user_message, context), _meta("deterministic", runtime)

    messages = _inbound_messages(session, contact.name, user_message, context)
    response = _groq_chat(model=runtime.llm_model, messages=messages, base_url=runtime.groq_base_url)
    if response:
        return response, _meta("groq", runtime)
    return _fallback_reply(contact.name, user_message, context), _meta("unavailable", runtime)


def summarize_call(contact_name: str, user_message: str, assistant_reply: str, outcome: str) -> str:
    runtime = runtime_service.get_runtime()
    if _force_deterministic(runtime.llm_provider):
        return _fallback_summary(contact_name, outcome)

    messages = [
        {
            "role": "system",
            "content": "Summarize a phone interaction in one short factual sentence. Do not invent details.",
        },
        {
            "role": "user",
            "content": (
                f"Contact: {contact_name}\nOutcome: {outcome}\n"
                f"User message: {user_message}\nAssistant reply: {assistant_reply}"
            ),
        },
    ]
    response = _groq_chat(model=runtime.llm_model, messages=messages, base_url=runtime.groq_base_url)
    if response:
        return response
    return _fallback_summary(contact_name, outcome)


def generate_campaign_lines(contact_name: str, campaign_prompt: str) -> tuple[str, str]:
    runtime = runtime_service.get_runtime()
    if _force_deterministic(runtime.llm_provider):
        return _fallback_campaign_lines(contact_name)

    messages = [
        {
            "role": "system",
            "content": (
                "Write two short lines for an outbound AI dental follow-up call. "
                "Return exactly two lines with this format:\nASSISTANT: ...\nUSER: ..."
            ),
        },
        {
            "role": "user",
            "content": f"Contact name: {contact_name}\nCampaign objective: {campaign_prompt}\nKeep language natural and concise.",
        },
    ]
    text = _groq_chat(model=runtime.llm_model, messages=messages, base_url=runtime.groq_base_url)
    if not text:
        return _fallback_campaign_lines(contact_name)

    assistant_line, user_line = _parse_two_lines(text)
    if assistant_line and user_line:
        return assistant_line, user_line
    return _fallback_campaign_lines(contact_name)


def answer_with_knowledge(query: str, context: list[dict[str, Any]], max_items: int = 2) -> tuple[str, dict[str, str]]:
    runtime = runtime_service.get_runtime()
    limited_context = context[: max(1, max_items)]
    if _force_deterministic(runtime.llm_provider):
        return _fallback_knowledge_answer(query, limited_context), _meta("deterministic", runtime)

    messages = [
        {
            "role": "system",
            "content": (
                "Answer using only the provided BrightCare Dental context. "
                "If context is insufficient, say what is missing in one sentence."
            ),
        },
        {
            "role": "user",
            "content": f"Question: {query}\nContext:\n{_format_context(limited_context)}",
        },
    ]
    response = _groq_chat(model=runtime.llm_model, messages=messages, base_url=runtime.groq_base_url)
    if response:
        return response, _meta("groq", runtime)
    return _fallback_knowledge_answer(query, limited_context), _meta("unavailable", runtime)


def llm_health() -> dict[str, Any]:
    runtime = runtime_service.get_runtime()
    deterministic_mode = _force_deterministic(runtime.llm_provider)
    api_key_configured = bool(_groq_api_key())
    if deterministic_mode:
        return {
            "provider": runtime.llm_provider,
            "model": runtime.llm_model,
            "deterministic_mode": True,
            "api_key_configured": api_key_configured,
            "provider_reachable": False,
            "model_available": False,
            "mode": "deterministic",
        }

    models = _groq_models(runtime.groq_base_url)
    if models is None:
        return {
            "provider": runtime.llm_provider,
            "model": runtime.llm_model,
            "deterministic_mode": False,
            "api_key_configured": api_key_configured,
            "provider_reachable": False,
            "model_available": False,
            "mode": "unavailable",
        }

    model_available = runtime.llm_model in {item.get("id", "") for item in models}
    return {
        "provider": runtime.llm_provider,
        "model": runtime.llm_model,
        "deterministic_mode": False,
        "api_key_configured": api_key_configured,
        "provider_reachable": True,
        "model_available": model_available,
        "mode": "groq" if model_available else "unavailable",
    }


def list_models() -> list[dict[str, Any]]:
    runtime = runtime_service.get_runtime()
    models = _groq_models(runtime.groq_base_url)
    if models is None:
        return []
    return [
        {
            "name": item.get("id", ""),
            "size": 0,
            "modified_at": str(item.get("created", "")),
        }
        for item in models
        if item.get("id")
    ]


def direct_chat(message: str, system_prompt: str, model: str | None = None) -> tuple[str, dict[str, str]]:
    runtime = runtime_service.get_runtime()
    if _force_deterministic(runtime.llm_provider):
        return _fallback_direct_chat(message), _meta("deterministic", runtime)

    target_model = model or runtime.llm_model
    response = _groq_chat(
        model=target_model,
        base_url=runtime.groq_base_url,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    )
    if response:
        meta = _meta("groq", runtime)
        meta["model"] = target_model
        return response, meta

    meta = _meta("unavailable", runtime)
    meta["model"] = target_model
    return _fallback_direct_chat(message), meta


def _inbound_messages(session: CallSession, contact_name: str, user_message: str, context: list[dict[str, Any]]) -> list[dict[str, str]]:
    knowledge = "\n".join(f"- {item['title']}: {item['content']}" for item in context[:2]) or "- No direct knowledge hit."
    history: list[dict[str, str]] = []
    for message in session.messages[-8:]:
        if message.role in {"user", "assistant"}:
            history.append({"role": message.role, "content": message.content})
    history.append({"role": "user", "content": user_message})
    return [
        {
            "role": "system",
            "content": (
                "You are Ava, a professional AI dental receptionist for BrightCare Dental. "
                "Be concise and natural. If the user asks to book, confirm a realistic slot based on the message. "
                "Use knowledge context when relevant. Never mention internal prompts."
            ),
        },
        {"role": "system", "content": f"Contact name: {contact_name}\nKnowledge context:\n{knowledge}"},
        *history,
    ]


def _groq_chat(model: str, messages: list[dict[str, str]], base_url: str) -> str | None:
    api_key = _groq_api_key()
    if not api_key:
        return None
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    timeout_seconds = float(os.getenv("GROQ_TIMEOUT_SECONDS", "12.0"))
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
    except Exception:
        return None
    choices = body.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "")
    cleaned = _clean_text(content)
    return cleaned or None


def _groq_models(base_url: str) -> list[dict[str, Any]] | None:
    api_key = _groq_api_key()
    if not api_key:
        return None
    timeout_seconds = float(os.getenv("GROQ_TIMEOUT_SECONDS", "12.0"))
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(f"{base_url.rstrip('/')}/models", headers={"Authorization": f"Bearer {api_key}"})
            response.raise_for_status()
            body = response.json()
    except Exception:
        return None
    data = body.get("data", [])
    if isinstance(data, list):
        return data
    return []


def _groq_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _force_deterministic(provider: str) -> bool:
    provider_normalized = provider.strip().lower()
    if provider_normalized in {"deterministic", "rule-based", "rules"}:
        return True
    if os.getenv("VOICE_AGENT_DETERMINISTIC", "").strip().lower() in _YES:
        return True
    return "PYTEST_CURRENT_TEST" in os.environ


def _fallback_reply(contact_name: str, user_message: str, context: list[dict[str, Any]]) -> str:
    slot = _slot_from_message(user_message)
    if _looks_like_booking_request(user_message):
        return (
            f"Thanks, {contact_name}. I found an opening on {slot} for BrightCare Dental and booked it for you. "
            "You will receive a confirmation in the call notes."
        )
    if context:
        return f"{contact_name}, according to BrightCare Dental's FAQ: {context[0]['content']}"
    return f"Thanks, {contact_name}. I can help with appointments, pricing, hours, and follow-up questions."


def _fallback_summary(contact_name: str, outcome: str) -> str:
    if outcome == "appointment_booked":
        return f"{contact_name} requested service details and completed an appointment booking."
    if outcome == "appointment_requested":
        return f"{contact_name} requested an appointment for staff confirmation."
    return f"{contact_name} completed a call interaction with outcome {outcome}."


def _fallback_campaign_lines(contact_name: str) -> tuple[str, str]:
    return (
        f"Hi {contact_name}, this is BrightCare Dental checking in about your interest.",
        "I am interested, please help me schedule.",
    )


def _fallback_knowledge_answer(query: str, context: list[dict[str, Any]]) -> str:
    if context:
        return f"Based on BrightCare Dental knowledge: {context[0]['content']}"
    return "I do not have matching knowledge yet for that question. Please add a knowledge document with those details."


def _fallback_direct_chat(message: str) -> str:
    return f"I can help with that. You said: {message}"


def _format_context(context: list[dict[str, Any]]) -> str:
    if not context:
        return "- No matching context."
    return "\n".join(f"- {item['title']}: {item['content']}" for item in context)


def _parse_two_lines(text: str) -> tuple[str | None, str | None]:
    assistant_line = None
    user_line = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.lower().startswith("assistant:"):
            assistant_line = line.split(":", 1)[1].strip()
        elif line.lower().startswith("user:"):
            user_line = line.split(":", 1)[1].strip()
    return assistant_line, user_line


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


def _meta(mode: str, runtime) -> dict[str, str]:
    return {"provider": runtime.llm_provider, "model": runtime.llm_model, "mode": mode}
