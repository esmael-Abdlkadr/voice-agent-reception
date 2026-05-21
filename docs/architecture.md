# Architecture

## Shape

```text
Browser voice or typed input
-> Next.js dashboard and playground
-> FastAPI agent endpoint
-> Groq LLM, deterministic tools, and local knowledge search
-> transcript, summary, outcome, and appointment storage
```

## Apps

- `apps/web`: Next.js App Router UI with responsive dashboard, call views, appointments, contacts, campaigns, knowledge, playground, and settings.
- `apps/api`: FastAPI service with routers for health, contacts, appointments, calls, campaigns, knowledge, agent, and analytics.
- `infra/docker`: local Postgres, Qdrant, and MinIO services.

## Storage

The app uses Postgres by default through a JSONB-backed persistence adapter. This keeps the v2 backend simple while giving contacts, campaigns, calls, transcripts, appointments, and knowledge documents durable local storage.

Automated tests use an explicit memory backend so they can run without a Docker daemon. That memory backend is not the normal app storage mode.

## Production Path

For real phone systems, add LiveKit for realtime media, SIP trunking for inbound/outbound calls, AMD for voicemail detection, voicemail drop for campaigns, and Docker-based VPS deployment.
