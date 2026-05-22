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
    "You are an AI customer support agent on a voice call. Be warm, concise, "
    "and accurate. Keep responses to one or two short sentences unless the "
    "caller asks for more detail. Use search_knowledge_base for factual "
    "questions about the company, product, hours, pricing, or policies. Use "
    "the workspace-specific tools when their description matches the user's "
    "need. Call escalate_to_human if the caller explicitly asks for a person, "
    "expresses anger, or the issue is outside what you can answer."
)
DEFAULT_GREETING = "Hi, thanks for calling. How can I help today?"


# -----------------------------------------------------------------------------
# Tool factories
#
# We build FunctionTool instances dynamically because each workspace
# configures its own webhook tools. Each factory closes over the workspace
# context and returns a livekit-agents FunctionTool the Agent can invoke.
# -----------------------------------------------------------------------------


def make_kb_tool(
    http_client: httpx.AsyncClient,
    api_base_url: str,
    workspace_id: int,
    tool_log: list[dict[str, Any]],
    clock: "Clock",
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
            return "Knowledge base search failed."

    return search


def make_webhook_tool(
    tool_cfg: dict[str, Any],
    http_client: httpx.AsyncClient,
    tool_log: list[dict[str, Any]],
    clock: "Clock",
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
            if not ok:
                return f"The {name} tool returned an error (HTTP {response.status_code}). Apologize to the caller and suggest a human follow-up."
            # Truncate to keep the LLM context lean
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
            return f"The {name} tool is unreachable right now. Apologize to the caller and suggest a human follow-up."

    return call_webhook


def make_escalate_tool(
    escalation_state: dict[str, Any],
    tool_log: list[dict[str, Any]],
    clock: "Clock",
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
        return (
            "Of course — I'll get someone from our team to follow up shortly. "
            "Can I confirm the best number or email to reach you at?"
        )

    return escalate


class Clock:
    """Holds the monotonic origin so tools can compute relative ts_ms."""

    def __init__(self) -> None:
        self.start = time.monotonic()

    def now_ms(self) -> int:
        return int((time.monotonic() - self.start) * 1000)


class ConfiguredAgent(Agent):
    """Agent class; all tools are passed in as a list at construction."""

    def __init__(self, instructions: str, tools: list[Any]) -> None:
        super().__init__(instructions=instructions, tools=tools)


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()

    participant = await ctx.wait_for_participant()

    metadata: dict[str, Any] = {}
    if participant.metadata:
        try:
            metadata = json.loads(participant.metadata)
        except json.JSONDecodeError:
            log.exception("Could not parse participant metadata: %r", participant.metadata)

    workspace_id = metadata.get("workspace_id")
    agent_id = metadata.get("agent_id")
    api_token = metadata.get("api_token")
    api_base_url = metadata.get("api_base_url", "http://localhost:8000")

    if not (isinstance(workspace_id, int) and isinstance(agent_id, int) and api_token):
        log.error(
            "Missing or invalid metadata: workspace_id=%r agent_id=%r has_token=%s",
            workspace_id,
            agent_id,
            bool(api_token),
        )
        return

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

    # Fetch the workspace's webhook tools so we can register them dynamically.
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

    # Build the tools list: KB + webhook tools + escalation.
    tools = [
        make_kb_tool(http_client, api_base_url, workspace_id, tool_calls_log, clock),
        make_escalate_tool(escalation_state, tool_calls_log, clock),
    ]
    for t in workspace_tools:
        try:
            tools.append(make_webhook_tool(t, http_client, tool_calls_log, clock))
        except Exception:
            log.exception("Failed to register webhook tool %s", t.get("name"))

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
        turns_log.append(
            {
                "role": "user" if role_raw == "user" else "agent",
                "text": text,
                "ts_ms": clock.now_ms(),
                "audio_ms": None,
            }
        )

    await session.start(agent=agent, room=ctx.room)

    # Tell the API the call has started so the live dashboard sees it
    # immediately. Idempotent on the API side (upsert by livekit_room_id).
    try:
        await http_client.post(
            f"{api_base_url}/workspaces/{workspace_id}/calls",
            json={
                "agent_id": agent_id,
                "livekit_room_id": ctx.room.name,
                "caller_identity": participant.identity,
                "started_at": call_started_at.isoformat(),
                "status": "active",
                "turns": [],
                "tool_calls": [],
            },
            timeout=5.0,
        )
    except Exception:
        log.exception("Failed to register call start with API")

    await session.generate_reply(
        instructions=f"Greet the caller. Say something like: {greeting!r}"
    )

    async def persist_call() -> None:
        call_ended_at = datetime.now(timezone.utc)
        duration_ms = clock.now_ms()
        status = "escalated" if escalation_state["escalated"] else "completed"
        payload: dict[str, Any] = {
            "agent_id": agent_id,
            "livekit_room_id": ctx.room.name,
            "caller_identity": participant.identity,
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
