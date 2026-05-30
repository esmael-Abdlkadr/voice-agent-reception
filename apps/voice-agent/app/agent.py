"""Workspace-aware voice receptionist worker.

On every call:
  1. Read participant metadata for workspace_id, agent_id, api_token, api_base_url
  2. Fetch the Agent config (persona, voice, llm) from the API
  3. Fetch the workspace's webhook Tools and register each as a function_tool
     the LLM can invoke. The tool's function POSTs to the configured URL and
     returns the response back to the LLM.
  4. Always register `search_knowledge_base` (workspace KB) and
     `escalate_to_human` (mark call escalated) as built-in tools.
  5. Capture transcript + tool-call events; persist to /calls at session
     start (status=active) and again at shutdown (status=completed or
     escalated).
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import cartesia, deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")

log = logging.getLogger("voice-agent")
logging.basicConfig(level=logging.INFO)

DEFAULT_CARTESIA_VOICE = os.getenv(
    "CARTESIA_VOICE_ID", "694f9389-aac1-45b6-b726-9d9369183238"
)
DEFAULT_GROQ_MODEL = os.getenv("GROQ_CHAT_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_API_KEY = os.environ["GROQ_API_KEY"]


DEFAULT_PERSONA = (
    "You are a warm, professional hotel concierge on a voice call. Keep replies "
    "to one or two short sentences. Use search_knowledge_base for questions "
    "about rooms, rates, amenities, check-in/out, and policies, and answer only "
    "from what it returns. Take room reservation requests with create_reservation. "
    "Call escalate_to_human if the guest explicitly asks for a person, is upset, "
    "or needs something you cannot do. Never invent prices or availability."
)
DEFAULT_GREETING = "Thank you for calling. How may I help you today?"


def make_kb_tool(
    http_client: httpx.AsyncClient,
    api_base_url: str,
    workspace_id: int,
    tool_log: list[dict[str, Any]],
    clock: "Clock",
    fire_stream,
):
    @function_tool(
        name="search_knowledge_base",
        description=(
            "Search the workspace's knowledge base for information relevant to "
            "the caller's question. Call this for factual questions about the "
            "company, product, hours, pricing, or any policy. Returns the top "
            "matching chunks as a string."
        ),
    )
    async def search(query: str) -> str:
        ts_ms = clock.now_ms()
        started = time.monotonic()
        try:
            response = await http_client.post(
                f"{api_base_url}/workspaces/{workspace_id}/knowledge/search",
                json={"query": query, "limit": 3},
                timeout=10.0,
            )
            response.raise_for_status()
            hits = response.json().get("hits", [])
            duration_ms = int((time.monotonic() - started) * 1000)
            tool_log.append(
                {
                    "tool_name": "search_knowledge_base",
                    "args_json": {"query": query},
                    "result_json": {"hit_count": len(hits)},
                    "ts_ms": ts_ms,
                    "duration_ms": duration_ms,
                    "status": "success",
                }
            )
            fire_stream(
                "tool_call",
                tool_name="search_knowledge_base",
                status="success",
                ts_ms=ts_ms,
                duration_ms=duration_ms,
            )
            if not hits:
                return "No relevant information found in the knowledge base."
            return "\n---\n".join(f"From {h['filename']}: {h['text']}" for h in hits)
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            log.exception("KB search failed")
            tool_log.append(
                {
                    "tool_name": "search_knowledge_base",
                    "args_json": {"query": query},
                    "result_json": {"error": str(exc)},
                    "ts_ms": ts_ms,
                    "duration_ms": duration_ms,
                    "status": "error",
                }
            )
            fire_stream(
                "tool_call",
                tool_name="search_knowledge_base",
                status="error",
                ts_ms=ts_ms,
                duration_ms=duration_ms,
            )
            return "Knowledge base search failed."

    return search


def make_webhook_tool(
    tool_cfg: dict[str, Any],
    http_client: httpx.AsyncClient,
    tool_log: list[dict[str, Any]],
    clock: "Clock",
    fire_stream,
):
    """Build a FunctionTool that POSTs the LLM's query to a configured webhook.

    Tool signature is always `(query: str) -> str`. The configured
    description (from the dashboard) tells the LLM when to call it.
    """
    name = tool_cfg["name"]
    description = tool_cfg["description"]
    webhook_url = tool_cfg["webhook_url"]
    auth_header = tool_cfg.get("auth_header") or None

    @function_tool(name=name, description=description)
    async def call_webhook(query: str) -> str:
        ts_ms = clock.now_ms()
        started = time.monotonic()
        headers = {"Content-Type": "application/json"}
        if auth_header:
            headers["Authorization"] = auth_header
        try:
            response = await http_client.post(
                webhook_url,
                json={"query": query},
                headers=headers,
                timeout=10.0,
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            body = response.text
            ok = 200 <= response.status_code < 300
            tool_log.append(
                {
                    "tool_name": name,
                    "args_json": {"query": query},
                    "result_json": {
                        "status_code": response.status_code,
                        "body_preview": body[:200],
                    },
                    "ts_ms": ts_ms,
                    "duration_ms": duration_ms,
                    "status": "success" if ok else "error",
                }
            )
            fire_stream(
                "tool_call",
                tool_name=name,
                status="success" if ok else "error",
                ts_ms=ts_ms,
                duration_ms=duration_ms,
            )
            if not ok:
                return f"The {name} tool returned an error (HTTP {response.status_code}). Apologize to the caller and suggest a human follow-up."
            return body[:2000]
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            log.exception("Webhook tool %s failed", name)
            tool_log.append(
                {
                    "tool_name": name,
                    "args_json": {"query": query},
                    "result_json": {"error": str(exc)},
                    "ts_ms": ts_ms,
                    "duration_ms": duration_ms,
                    "status": "error",
                }
            )
            fire_stream(
                "tool_call",
                tool_name=name,
                status="error",
                ts_ms=ts_ms,
                duration_ms=duration_ms,
            )
            return f"The {name} tool is unreachable right now. Apologize to the caller and suggest a human follow-up."

    return call_webhook


def make_escalate_tool(
    escalation_state: dict[str, Any],
    tool_log: list[dict[str, Any]],
    clock: "Clock",
    fire_stream,
):
    @function_tool(
        name="escalate_to_human",
        description=(
            "Hand the conversation off to a human teammate. Call this when "
            "the caller explicitly asks for a person, expresses serious "
            "frustration, or has a request outside what you can answer "
            "(refunds, complex billing, complaints). Provide a one-sentence "
            "`reason` summarizing why you're escalating. Returns the line "
            "you should say to the caller before hanging up."
        ),
    )
    async def escalate(reason: str) -> str:
        ts_ms = clock.now_ms()
        escalation_state["escalated"] = True
        escalation_state["reason"] = reason
        tool_log.append(
            {
                "tool_name": "escalate_to_human",
                "args_json": {"reason": reason},
                "result_json": {"acknowledged": True},
                "ts_ms": ts_ms,
                "duration_ms": 0,
                "status": "success",
            }
        )
        fire_stream(
            "tool_call",
            tool_name="escalate_to_human",
            status="success",
            ts_ms=ts_ms,
            duration_ms=0,
        )
        return (
            "Of course — I'll get someone from our team to follow up shortly. "
            "Can I confirm the best number or email to reach you at?"
        )

    return escalate


def make_reservation_tool(
    http_client: httpx.AsyncClient,
    api_base_url: str,
    workspace_id: int,
    caller_phone: str,
    tool_log: list[dict[str, Any]],
    clock: "Clock",
    fire_stream,
):
    @function_tool(
        name="create_reservation",
        description=(
            "Record a hotel reservation request AFTER you have the guest's full "
            "name, check-in and check-out dates, room type, and number of guests, "
            "and you have read them back to confirm. check_in and check_out must be "
            "YYYY-MM-DD (resolve relative dates like 'this Friday' from today's date "
            "in your instructions). check_out must be after check_in."
        ),
    )
    async def create_reservation(
        guest_name: str,
        check_in: str,
        check_out: str,
        room_type: str = "",
        num_guests: int = 1,
        notes: str = "",
    ) -> str:
        ts_ms = clock.now_ms()
        started = time.monotonic()
        payload: dict[str, Any] = {
            "guest_name": guest_name,
            "check_in": check_in,
            "check_out": check_out,
            "room_type": room_type,
            "num_guests": num_guests,
            "notes": notes,
        }
        if caller_phone and caller_phone.startswith("+"):
            payload["guest_phone"] = caller_phone
        try:
            resp = await http_client.post(
                f"{api_base_url}/workspaces/{workspace_id}/reservations",
                json=payload,
                timeout=10.0,
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            if resp.status_code == 422:
                tool_log.append({
                    "tool_name": "create_reservation",
                    "args_json": {"check_in": check_in, "check_out": check_out},
                    "result_json": {"error": "invalid_dates"},
                    "ts_ms": ts_ms, "duration_ms": duration_ms, "status": "error",
                })
                fire_stream("tool_call", tool_name="create_reservation", status="error",
                            ts_ms=ts_ms, duration_ms=duration_ms)
                return "Those dates aren't valid — check-out must be after check-in. Clarify the dates with the guest."
            resp.raise_for_status()
            res = resp.json()
            tool_log.append({
                "tool_name": "create_reservation",
                "args_json": {"guest_name": guest_name, "check_in": check_in,
                              "check_out": check_out, "room_type": room_type,
                              "num_guests": num_guests},
                "result_json": {"reservation_id": res.get("id")},
                "ts_ms": ts_ms, "duration_ms": duration_ms, "status": "success",
            })
            fire_stream("tool_call", tool_name="create_reservation", status="success",
                        ts_ms=ts_ms, duration_ms=duration_ms)
            return "Reservation recorded successfully."
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            log.exception("create_reservation failed")
            tool_log.append({
                "tool_name": "create_reservation",
                "args_json": {"guest_name": guest_name},
                "result_json": {"error": str(exc)},
                "ts_ms": ts_ms, "duration_ms": duration_ms, "status": "error",
            })
            fire_stream("tool_call", tool_name="create_reservation", status="error",
                        ts_ms=ts_ms, duration_ms=duration_ms)
            return "I couldn't record the reservation just now. Offer to take their details for a callback."

    return create_reservation


def make_lookup_tool(
    http_client: httpx.AsyncClient,
    api_base_url: str,
    workspace_id: int,
    caller_phone: str,
    tool_log: list[dict[str, Any]],
    clock: "Clock",
    fire_stream,
):
    @function_tool(
        name="look_up_reservation",
        description=(
            "Look up a guest's existing reservations to tell them whether a "
            "booking exists and its status. Pass the guest's full name. Use this "
            "whenever a caller asks to check, confirm, or find their reservation."
        ),
    )
    async def look_up_reservation(guest_name: str = "") -> str:
        ts_ms = clock.now_ms()
        started = time.monotonic()
        params: dict[str, Any] = {}
        if guest_name.strip():
            params["name"] = guest_name.strip()
        if caller_phone and caller_phone.startswith("+"):
            params["phone"] = caller_phone
        if not params:
            return "Ask the guest for the name the reservation is under, then try again."
        try:
            resp = await http_client.get(
                f"{api_base_url}/workspaces/{workspace_id}/reservations/lookup",
                params=params,
                timeout=10.0,
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            resp.raise_for_status()
            results = resp.json()
            tool_log.append({
                "tool_name": "look_up_reservation",
                "args_json": {"name": guest_name},
                "result_json": {"match_count": len(results)},
                "ts_ms": ts_ms, "duration_ms": duration_ms, "status": "success",
            })
            fire_stream("tool_call", tool_name="look_up_reservation", status="success",
                        ts_ms=ts_ms, duration_ms=duration_ms)
            if not results:
                return "No reservation was found under that name. Offer to take a new reservation."
            lines = []
            for r in results[:3]:
                lines.append(
                    f"{r.get('room_type') or 'a room'} from {r['check_in']} to "
                    f"{r['check_out']} for {r['num_guests']} guest(s), status "
                    f"{r['status']}"
                )
            return "Found: " + "; ".join(lines) + ". Read this back to the guest."
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            log.exception("look_up_reservation failed")
            tool_log.append({
                "tool_name": "look_up_reservation",
                "args_json": {"name": guest_name},
                "result_json": {"error": str(exc)},
                "ts_ms": ts_ms, "duration_ms": duration_ms, "status": "error",
            })
            fire_stream("tool_call", tool_name="look_up_reservation", status="error",
                        ts_ms=ts_ms, duration_ms=duration_ms)
            return "I couldn't check that just now. Offer to take their details for a callback."

    return look_up_reservation


class Clock:
    """Holds the monotonic origin so tools can compute relative ts_ms."""

    def __init__(self) -> None:
        self.start = time.monotonic()

    def now_ms(self) -> int:
        return int((time.monotonic() - self.start) * 1000)


import re as _re

_LEAK_MARKER = _re.compile(r"<\s*\|?\s*(function|tool_call|\|?python)", _re.IGNORECASE)


async def _sanitize_text_stream(text):
    """Pass text through, but drop everything from the first tool-call leak
    marker onward. Keeps a small tail so a marker split across chunks is caught."""
    buf = ""
    cutting = False
    async for chunk in text:
        if cutting:
            continue
        buf += chunk
        m = _LEAK_MARKER.search(buf)
        if m:
            safe = buf[: m.start()]
            if safe:
                yield safe
            cutting = True
            buf = ""
            continue
        if len(buf) > 16:
            yield buf[:-16]
            buf = buf[-16:]
    if not cutting and buf:
        yield buf


_EMPTY_FALLBACK = "I'm sorry, could you say that again for me?"


async def _sanitized_or_fallback(text):
    spoke = False
    async for chunk in _sanitize_text_stream(text):
        if chunk.strip():
            spoke = True
        yield chunk
    if not spoke:
        yield _EMPTY_FALLBACK


class ConfiguredAgent(Agent):
    """Agent whose spoken + transcribed text is sanitized of any tool-call
    syntax the LLM may leak as plain text."""

    def __init__(self, instructions: str, tools: list[Any]) -> None:
        super().__init__(instructions=instructions, tools=tools)

    async def tts_node(self, text, model_settings):
        async for frame in Agent.default.tts_node(
            self, _sanitized_or_fallback(text), model_settings
        ):
            yield frame

    async def transcription_node(self, text, model_settings):
        async for chunk in Agent.default.transcription_node(
            self, _sanitized_or_fallback(text), model_settings
        ):
            yield chunk


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()

    participant = await ctx.wait_for_participant()

    metadata: dict[str, Any] = {}
    if participant.metadata:
        try:
            metadata = json.loads(participant.metadata)
        except json.JSONDecodeError:
            log.exception("Could not parse participant metadata: %r", participant.metadata)

    api_base_url = metadata.get("api_base_url") or os.getenv(
        "API_PUBLIC_URL", "http://localhost:8000"
    )
    attrs = dict(getattr(participant, "attributes", {}) or {})
    dialed_number = attrs.get("sip.trunkPhoneNumber") or attrs.get("sip.dialedNumber")
    caller_number = attrs.get("sip.phoneNumber")

    browser_workspace_id = metadata.get("workspace_id")
    browser_agent_id = metadata.get("agent_id")
    browser_api_token = metadata.get("api_token")

    if isinstance(browser_workspace_id, int) and isinstance(browser_agent_id, int) and browser_api_token:
        workspace_id = browser_workspace_id
        agent_id = browser_agent_id
        api_token = browser_api_token
        caller_identity = participant.identity
        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        try:
            cfg_response = await http_client.get(
                f"{api_base_url}/workspaces/{workspace_id}/agents/{agent_id}"
            )
            cfg_response.raise_for_status()
            agent_cfg = cfg_response.json()
        except Exception:
            log.exception("Failed to fetch agent config for ws=%s agent=%s", workspace_id, agent_id)
            await http_client.aclose()
            return
    elif dialed_number:
        service_key = os.getenv("SERVICE_API_KEY", "dev-service-key-change-me")
        api_token = service_key
        caller_identity = caller_number or participant.identity
        http_client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {service_key}"},
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        try:
            resolve_response = await http_client.get(
                f"{api_base_url}/internal/resolve-number",
                params={"e164": dialed_number},
            )
            resolve_response.raise_for_status()
            resolved = resolve_response.json()
            workspace_id = resolved["workspace_id"]
            agent_id = resolved["agent_id"]
            agent_cfg = resolved["agent"]
        except Exception:
            log.exception("Failed to resolve dialed number %s", dialed_number)
            await http_client.aclose()
            return
        log.info("Inbound phone call: dialed=%s caller=%s -> ws=%s agent=%s",
                 dialed_number, caller_identity, workspace_id, agent_id)
    else:
        log.error(
            "Unroutable call: no browser metadata and no SIP dialed number. attrs=%s",
            attrs,
        )
        return

    workspace_tools: list[dict[str, Any]] = []
    try:
        tools_response = await http_client.get(
            f"{api_base_url}/workspaces/{workspace_id}/tools"
        )
        if tools_response.is_success:
            workspace_tools = tools_response.json()
    except Exception:
        log.exception("Failed to fetch workspace tools; continuing without dynamic tools")

    persona = (agent_cfg.get("persona_prompt") or "").strip() or DEFAULT_PERSONA
    greeting = (agent_cfg.get("greeting") or "").strip() or DEFAULT_GREETING
    voice_id = (agent_cfg.get("voice_id") or "").strip() or DEFAULT_CARTESIA_VOICE
    llm_model = (agent_cfg.get("llm_model") or "").strip() or DEFAULT_GROQ_MODEL

    log.info(
        "Starting call: workspace=%s agent=%s voice=%s model=%s tools=%d",
        workspace_id,
        agent_id,
        voice_id,
        llm_model,
        len(workspace_tools),
    )

    clock = Clock()
    call_started_at = datetime.now(timezone.utc)
    tool_calls_log: list[dict[str, Any]] = []
    escalation_state: dict[str, Any] = {"escalated": False, "reason": None}
    room_name = ctx.room.name

    async def stream(kind: str, **fields: Any) -> None:
        try:
            await http_client.post(
                f"{api_base_url}/workspaces/{workspace_id}/calls/stream",
                json={"livekit_room_id": room_name, "kind": kind, **fields},
                timeout=5.0,
            )
        except Exception:
            log.debug("stream event failed", exc_info=True)

    def fire_stream(kind: str, **fields: Any) -> None:
        try:
            import asyncio

            asyncio.create_task(stream(kind, **fields))
        except RuntimeError:
            pass

    tools = [
        make_kb_tool(http_client, api_base_url, workspace_id, tool_calls_log, clock, fire_stream),
        make_escalate_tool(escalation_state, tool_calls_log, clock, fire_stream),
    ]
    for t in workspace_tools:
        try:
            tools.append(
                make_webhook_tool(t, http_client, tool_calls_log, clock, fire_stream)
            )
        except Exception:
            log.exception("Failed to register webhook tool %s", t.get("name"))

    tools.append(
        make_reservation_tool(
            http_client, api_base_url, workspace_id, caller_identity,
            tool_calls_log, clock, fire_stream,
        )
    )
    tools.append(
        make_lookup_tool(
            http_client, api_base_url, workspace_id, caller_identity,
            tool_calls_log, clock, fire_stream,
        )
    )
    today_local = datetime.now(timezone.utc)
    persona += (
        f"\n\nToday's date is {today_local.strftime('%A, %B %d, %Y')}. You can take "
        "room reservations and check existing ones.\n"
        "To take a NEW reservation, gather these details ONE AT A TIME, asking a "
        "single question and waiting for the answer before the next: (a) the "
        "check-in date and number of nights, (b) the room type and number of "
        "guests, (c) the name for the reservation. Then repeat it back in one short "
        "sentence to confirm, and once they say yes, record it and tell them the "
        "front desk will follow up to finalize.\n"
        "To CHECK an existing reservation (when a guest asks whether their booking "
        "is done, or to confirm or find it), ask for the name it's under, then look "
        "it up and read back what you find. If nothing is found, say so kindly and "
        "offer to make one."
    )

    agent = ConfiguredAgent(instructions=persona, tools=tools)

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en"),
        llm=openai.LLM(
            model=llm_model,
            base_url=GROQ_BASE_URL,
            api_key=GROQ_API_KEY,
        ),
        tts=cartesia.TTS(model="sonic-2", voice=voice_id),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    turns_log: list[dict[str, Any]] = []

    @session.on("conversation_item_added")
    def _on_item_added(event: Any) -> None:
        item = getattr(event, "item", None) or event
        role_raw = getattr(item, "role", None)
        text = getattr(item, "text_content", None) or getattr(item, "content", None) or ""
        if isinstance(text, list):
            text = " ".join(str(part) for part in text if part)
        text = (text or "").strip()
        if not text or role_raw not in ("user", "assistant"):
            return
        role = "user" if role_raw == "user" else "agent"
        ts_ms = clock.now_ms()
        turns_log.append(
            {
                "role": role,
                "text": text,
                "ts_ms": ts_ms,
                "audio_ms": None,
            }
        )
        fire_stream("turn", role=role, text=text, ts_ms=ts_ms)

    await session.start(agent=agent, room=ctx.room)

    try:
        await http_client.post(
            f"{api_base_url}/workspaces/{workspace_id}/calls",
            json={
                "agent_id": agent_id,
                "livekit_room_id": ctx.room.name,
                "caller_identity": caller_identity,
                "started_at": call_started_at.isoformat(),
                "status": "active",
                "turns": [],
                "tool_calls": [],
            },
            timeout=5.0,
        )
    except Exception:
        log.exception("Failed to register call start with API")

    await session.say(greeting, allow_interruptions=False)

    async def persist_call() -> None:
        call_ended_at = datetime.now(timezone.utc)
        duration_ms = clock.now_ms()
        status = "escalated" if escalation_state["escalated"] else "completed"
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "livekit_room_id": ctx.room.name,
            "caller_identity": caller_identity,
            "started_at": call_started_at.isoformat(),
            "ended_at": call_ended_at.isoformat(),
            "status": status,
            "duration_ms": duration_ms,
            "turns": turns_log,
            "tool_calls": tool_calls_log,
        }
        if escalation_state["reason"]:
            payload["escalation_reason"] = escalation_state["reason"]
        try:
            response = await http_client.post(
                f"{api_base_url}/workspaces/{workspace_id}/calls",
                json=payload,
                timeout=15.0,
            )
            log.info(
                "Persisted call: status_code=%s call_status=%s turns=%d tool_calls=%d duration_ms=%d",
                response.status_code,
                status,
                len(turns_log),
                len(tool_calls_log),
                duration_ms,
            )
        except Exception:
            log.exception("Failed to persist call to API")
        finally:
            await http_client.aclose()

    ctx.add_shutdown_callback(persist_call)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
