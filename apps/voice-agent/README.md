# Voice Agent Worker

LiveKit Agents worker that powers the BrightCare Dental voice receptionist.
Audio pipeline: Deepgram STT -> Groq LLM -> Cartesia TTS, with Silero VAD and
the LiveKit multilingual turn detector.

## Setup

This service has its own virtualenv (kept separate from `apps/api` because the
LiveKit Agents dependency tree is large).

```bash
cd apps/voice-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Download the turn-detector model weights and any other prefetched assets.
python -m app.agent download-files
```

## Required environment variables

Add these to the repo-root `.env` (the worker loads it automatically):

```
# LiveKit Cloud (https://cloud.livekit.io)
LIVEKIT_URL=wss://<your-project>.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# Deepgram (https://console.deepgram.com)
DEEPGRAM_API_KEY=...

# Cartesia (https://play.cartesia.ai)
CARTESIA_API_KEY=...
CARTESIA_VOICE_ID=694f9389-aac1-45b6-b726-9d9369183238  # optional, defaults to a warm female voice

# Groq (already present in .env for apps/api)
GROQ_API_KEY=...
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_CHAT_MODEL=llama-3.1-8b-instant
```

## Running

```bash
source .venv/bin/activate
python -m app.agent dev   # auto-reload, verbose logs
# or
python -m app.agent start # production mode
```

The worker registers with LiveKit Cloud and auto-joins any room a participant
creates. Open the web playground at `http://localhost:3000/voice` and click
"Start call" to begin a session.

## Milestone status

- [x] M1 - voice "hello world" greeting
- [ ] M2 - orchestrator + Scheduling specialist
- [ ] M3 - patient identification + new patient flow
- [ ] M4 - filler phrases, interruption handling, transcript persistence
- [ ] M5+ - Knowledge, Triage, Billing specialists
