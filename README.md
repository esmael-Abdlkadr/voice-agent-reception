# VoiceAgentOS Platform

Open-source AI voice assistant platform for portfolio and client work. The platform runs locally with Postgres persistence and provides APIs for AI reception, appointment booking, outbound campaigns, RAG-style knowledge answers, transcripts, summaries, analytics, SIP configuration, AMD, voicemail templates, recordings, and runtime settings without paid APIs by default.

## What It Supports

- Inbound receptionist flow for BrightCare Dental.
- Browser voice or typed fallback in the playground.
- Twilio inbound phone receptionist flow with TwiML speech gathering.
- Appointment booking and call transcript logging.
- Outbound campaign simulation with local outcomes.
- Knowledge-base answers from seeded FAQ content.
- SIP trunk configuration and queued outbound call requests.
- Answer machine detection configuration and local analysis.
- Voicemail template management.
- Agent profiles and orchestration configuration.
- Recording metadata and cost estimates.
- Auth and role-based authorization for platform_admin, campaign_operator, and analyst roles.
- Dashboard metrics for calls, appointments, outcomes, and local platform cost.
- Production upgrade path for LiveKit, SIP, AMD, and voicemail drop.

## Docker Setup And Run

Project root:

```bash
cd /Users/apple/Documents/Codex/2026-05-04/well-i-want-to-start-new/voice-agent-demo
```

First-time setup:

```bash
 
docker compose up --build -d
```

Set `GROQ_API_KEY` in `.env` before live AI calls. Docker Compose now starts only local infrastructure; the LLM runs through Groq.

Run or restart infra services:

```bash
docker compose up -d
docker compose ps
```

Docker services started by compose:

- `postgres` on `5432`
- `qdrant` on `6333`
- `minio` on `9000/9001`

## Run API And Web

Backend API:

```bash
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
DATABASE_URL=postgresql://voice_agent:voice_agent@localhost:5432/voice_agent_demo \
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8007 --reload
```

In another terminal:

```bash
cd /Users/apple/Documents/Codex/2026-05-04/well-i-want-to-start-new/voice-agent-demo
npm install
npm run dev
```

URLs:

- Web app: `http://localhost:3000`
- Swagger docs: `http://127.0.0.1:8007/docs`

LLM runtime notes:

- Default backend LLM provider is `groq`.
- Default model is `llama-3.1-8b-instant`.
- Set `GROQ_API_KEY` in `.env` before testing live LLM calls.
- Tests can still force deterministic mode with `VOICE_AGENT_DETERMINISTIC=true`.
- LLM status endpoint: `GET /llm/health` (requires authenticated user role).
- Groq model endpoints: `GET /llm/models` and `POST /llm/chat`.
- Knowledge grounded answer endpoint: `POST /knowledge/answer`.

## Twilio Inbound Phone Setup

This integration uses Twilio Programmable Voice webhooks and TwiML `<Gather>` for a turn-based phone receptionist flow. It is designed for local testing with fake patient data.

Add these values to `.env`:

```bash
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
PUBLIC_WEBHOOK_BASE_URL=
TWILIO_VALIDATE_WEBHOOKS=false
```

Local test flow:

```bash
cd /Users/apple/Documents/Codex/2026-05-04/well-i-want-to-start-new/voice-agent-demo/apps/api
DATABASE_URL=postgresql://voice_agent:voice_agent@localhost:5432/voice_agent_demo \
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```bash
ngrok http 8000
```

Copy the HTTPS forwarding URL from ngrok and set:

```bash
PUBLIC_WEBHOOK_BASE_URL=https://your-ngrok-domain.ngrok.app
```

In the Twilio Console, configure your Twilio phone number Voice webhook:

```text
POST https://your-ngrok-domain.ngrok.app/twilio/voice/inbound
```

Optional status callback:

```text
POST https://your-ngrok-domain.ngrok.app/twilio/voice/status
```

Then call the Twilio number from a verified test phone number. The call should create a Twilio call session, log transcript messages, and create appointment requests with `status=requested`.

Twilio trial notes:

- Trial accounts can require verified caller/recipient numbers.
- Trial calls can play a Twilio trial message.
- Trial calls and minutes are limited.
- Keep `TWILIO_VALIDATE_WEBHOOKS=false` for first ngrok tests, then enable it after your public webhook URL is stable.

Safety note:

- This local project is not HIPAA-ready.
- Use fake patient data during development.
- Production healthcare use requires compliance review, BAA-ready vendors, secure deployment, retention controls, audit logs, and strict access policies.

## Seed Credentials

API seeded admin user:

- Email: `admin@voiceagent.local`
- Password: `admin123`
- Role: `platform_admin`

Notes:

- `campaign_operator` and `analyst` users are not seeded by default.
- Create additional users from Swagger using `POST /users` after logging in as admin.

Infrastructure default credentials:

- Postgres
- User: `voice_agent`
- Password: `voice_agent`
- Database: `voice_agent_demo`

- MinIO
- Access key: `voiceagent`
- Secret key: `voiceagentdemo`
- Console: `http://127.0.0.1:9001`

## Reset Stale Docker Data

If Docker shows old data, remove persisted volumes and start fresh:

```bash
cd /Users/apple/Documents/Codex/2026-05-04/well-i-want-to-start-new/voice-agent-demo
docker compose down --remove-orphans
rm -rf infra/docker/postgres-data infra/docker/qdrant-data infra/docker/minio-data infra/docker/ollama-data
docker compose up --build -d
```

Then restart the API command above so fresh seed data is loaded.

## Verification

```bash
BASE=http://127.0.0.1:8000 scripts/curl-test-api.sh
npm run test:api
npm --workspace apps/web run lint
npm --workspace apps/web run test
npm --workspace apps/web run build
```

The backend uses Postgres by default through `DATABASE_URL`. Automated tests set `VOICE_AGENT_STORAGE=memory` explicitly so they can run without a Docker daemon, but normal app development should use the Postgres service from Docker Compose.
