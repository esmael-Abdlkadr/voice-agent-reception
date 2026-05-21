# Voice Agent Architecture

> Status as of 2026-05-21. Multi-agent voice receptionist for BrightCare
> Dental. Milestone 1 ships a single agent; Milestone 2+ adds the
> orchestrator + specialist topology.

## High-level picture

```
Browser (Next.js /voice page)
   |  WebRTC audio
   v
LiveKit Cloud (SFU)
   |  audio frames
   v
apps/voice-agent (Python worker)
   |  Deepgram STT -> Groq LLM -> Cartesia TTS
   v
[M2+] Specialist sub-agents (Scheduling, Knowledge, Triage, Billing)
   |
   v
Postgres + Qdrant (existing)
```

The browser fetches a LiveKit JWT from `apps/api/livekit/token`, joins a
LiveKit room, and publishes its microphone. The voice-agent worker is already
registered with LiveKit Cloud and auto-joins the room. From there the agent
session handles the speech loop end to end.

## Components

### apps/voice-agent (new)

LiveKit Agents worker. Single Python process, separate venv from `apps/api`
because the LiveKit dependency tree is heavy. Loads the repo-root `.env`.

Key file: `apps/voice-agent/app/agent.py`.

### apps/api (touched)

New router `apps/api/app/routers/livekit.py` exposing `POST /livekit/token`.
Returns `{ token, url, room, identity }` for the browser to use. Adds
`livekit-api` to `requirements.txt`.

### apps/web (touched)

New page `apps/web/app/voice/page.tsx`. Click "Start call" -> mic permission
-> token fetch -> LiveKit room join. Uses `@livekit/components-react` for
the visualizer and audio rendering. Adds three `livekit-*` npm deps.

## Stack choices (and why)

| Layer | Choice | Why |
|---|---|---|
| Transport | LiveKit Cloud + WebRTC | Browser-first demo, free tier sufficient, same code path works with SIP later |
| Framework | LiveKit Agents (Python) | Built for orchestrator + specialists pattern, swap providers easily |
| STT | Deepgram nova-3 | ~150ms streaming, much faster than Whisper |
| LLM | Groq llama-3.1-8b-instant | ~500 tok/s makes multi-agent latency feasible |
| TTS | Cartesia sonic-2 | ~90ms first-byte, the fastest production TTS |
| VAD | Silero | Standard, runs locally |
| Turn detection | LiveKit multilingual model | Better than VAD alone at deciding when the caller is done speaking |

## Local run (three services)

Open three terminals from the repo root.

```bash
# 1. Infra (Postgres, Qdrant, MinIO)
docker-compose up -d

# 2. API
cd apps/api
source ../../.venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# 3. Voice agent worker
cd apps/voice-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.agent download-files   # one time, downloads model weights
python -m app.agent dev

# 4. Web
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000/voice and click "Start call".

## Milestone status

- [x] M1 - voice "hello world" greeting in browser
- [ ] M2 - orchestrator + Scheduling specialist (requires
      `packages/python-shared/` and real Provider/AppointmentType models)
- [ ] M3 - patient identification (name + DOB lookup) and new patient flow
- [ ] M4 - filler phrases, interruption handling, emergency keyword
      guardrail, transcript persisted to `calls`
- [ ] M5+ - Knowledge, Triage, Billing specialists

## Decisions captured

- Multi-agent topology: orchestrator (Groq LLM) + specialist sub-agents as
  pure async tool functions. Not swarm / handoff.
- Vertical slice first: voice + orchestrator + Scheduling end-to-end before
  adding more specialists.
- Repo layout: new `apps/voice-agent/`, shared Python code will go in a
  new `packages/python-shared/` once M2 needs DB models.
- Patient ID: mirror phone flow (name + DOB lookup in `contacts`) even in
  browser, so the same code works for Twilio later.
- Conversation state: in-memory per LiveKit session for v1; transcript
  persisted to `calls` after the call ends.
- Explicitly deferred: Twilio integration, HIPAA compliance, multi-tenant,
  real insurance data.
