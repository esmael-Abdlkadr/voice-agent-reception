"""BrightCare Dental voice receptionist worker (Milestone 1).

Joins a LiveKit room as the AI receptionist and runs a
Deepgram (STT) -> Groq (LLM) -> Cartesia (TTS) pipeline.

Milestone 1 scope: single agent, no specialist delegation. The
orchestrator + specialist topology lands in Milestone 2.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import cartesia, deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

_REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_REPO_ROOT / ".env")


RECEPTIONIST_INSTRUCTIONS = """\
You are the AI receptionist for BrightCare Dental, a friendly suburban dental
clinic.

Tone: warm, calm, professional. Speak naturally and concisely - you are on a
phone call, not writing an email. Keep responses to one or two short sentences
unless the caller asks for more detail. Never spell out URLs, email addresses,
or long numbers letter-by-letter unless asked.

You can help callers with:
  - Booking, rescheduling, or cancelling appointments
  - Answering common questions about hours, services, and location
  - Taking down concerns about urgent dental issues
  - Insurance and pricing questions at a high level

Important guardrails:
  - If the caller describes a true emergency (heavy bleeding, swelling that
    affects breathing, knocked-out tooth, severe trauma), tell them to hang up
    and call 911 or go to an emergency room.
  - You are an AI assistant, not a dentist. Do not give clinical diagnoses or
    medical advice; defer specifics to the dentist.
  - The call may be recorded for quality.

This is a Milestone 1 demo build. Scheduling, knowledge lookup, triage, and
billing tools are not wired in yet. If the caller asks you to perform something
you cannot actually do, acknowledge the limit honestly rather than pretending.
"""


class Receptionist(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=RECEPTIONIST_INSTRUCTIONS)


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect()

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="en"),
        llm=openai.LLM(
            model=os.getenv("GROQ_CHAT_MODEL", "llama-3.1-8b-instant"),
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=os.environ["GROQ_API_KEY"],
        ),
        tts=cartesia.TTS(
            model="sonic-2",
            voice=os.getenv(
                "CARTESIA_VOICE_ID",
                "694f9389-aac1-45b6-b726-9d9369183238",
            ),
        ),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
    )

    await session.start(agent=Receptionist(), room=ctx.room)

    await session.generate_reply(
        instructions=(
            "Greet the caller warmly. Introduce yourself as the AI receptionist "
            "at BrightCare Dental and ask how you can help today. Mention "
            "briefly that the call may be recorded for quality."
        )
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
