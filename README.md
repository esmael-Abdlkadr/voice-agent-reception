# VoiceOps

A multi-tenant voice-AI operations console for customer-support agencies.

Run AI voice agents for your clients, watch live calls roll in, configure
personas, ground answers in their knowledge base, give agents webhook tools
to call mid-conversation, and review every transcript — from a single
console.

```
   ░▒▒▒▒▒▒▒░     ░▒▒▒░     ░▒▒▒▒▒▒▒▒▒▒░     ░▒▒▒░     ░▒▒▒▒▒▒▒░
        Live   ·   Calls   ·   Agent   ·   Knowledge   ·   Tools
```

---

## What's in the box

**Per-workspace product surface**

- **Live** — Real-time view of active calls, today's snapshot, recent
  outcomes. Updates over server-sent events; no polling.
- **Calls** — Intercom-style list + transcript pane with tool-call
  timeline, deep-linkable URLs.
- **Agent** — Configure persona prompt, greeting, voice (Cartesia), LLM
  model (Groq). Browser-based "Test call" panel right next to the form.
- **Knowledge** — Upload `.txt` / `.md` / `.pdf`. Chunked and embedded
  locally with `sentence-transformers`, stored in Qdrant. Inline search
  test panel to verify retrieval quality.
- **Tools** — Define webhooks the agent can call mid-conversation (order
  lookups, account details, ticket creation). Each tool has a Live test
  panel that fires a sample request and shows the raw response.
- **Analytics** — 7d / 30d / 90d rollups: call volume, average duration,
  completion rate, daily breakdown, status distribution, top tools used.

**Built into every call**

- `search_knowledge_base` — RAG over the workspace's uploaded docs.
- `escalate_to_human` — Caller asks for a human → agent reads a handoff
  line → call persists with status `escalated` and a reason captured by
  the LLM.

---

## Stack

| Layer | Choice | Why |
|---|---|---|
| Voice transport | LiveKit Cloud + WebRTC | Browser-first today, swap in SIP for real phone calls without changing the worker |
| STT | Deepgram nova-3 | ~150 ms streaming, the latency budget needs it |
| LLM | Groq (Llama 3.1 / 3.3) | ~500 tok/s makes tool-using multi-turn dialogue feel real-time |
| TTS | Cartesia sonic-2 | ~90 ms first-byte; the agent doesn't sound robotic |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) | Runs locally on a Mac CPU; no extra API key |
| Vector store | Qdrant | Per-workspace collection, payload-filterable |
| Relational | Postgres + SQLAlchemy 2.0 + Alembic | Real foreign keys for workspaces → agents → calls → turns |
| Object store | MinIO | Recordings (post-V1) |
| API | FastAPI | Sync routes for CRUD, async SSE for live, asyncio bridge for the worker |
| Frontend | Next.js 14 (App Router) + Tailwind | Dark theme, Inter + JetBrains Mono, custom SVG charts |

---

## Architecture

```
                           ┌─────────────────┐
                           │  Browser (web)  │
                           │  Next.js 14     │
                           └────┬─────────┬──┘
                                │ HTTP +  │ EventSource (SSE)
                                │ JSON    │
                                ▼         ▼
                           ┌─────────────────┐         ┌──────────────────┐
                           │  API (FastAPI)  │◄────────│ Voice worker     │
                           │                 │  HTTP   │ (LiveKit Agents) │
                           │  Auth · CRUD ·  │         │  fetches Agent + │
                           │  SSE · upsert   │         │  Tools + KB; runs│
                           │  pub/sub        │         │  STT→LLM→TTS loop│
                           └────┬─────┬──────┘         └────────┬─────────┘
                                │     │                         │
                          ┌─────▼─┐ ┌─▼─────────┐               │ WebRTC
                          │ Pg    │ │  Qdrant   │               │
                          │       │ │ (KB chunks)               ▼
                          └───────┘ └───────────┘     ┌──────────────────┐
                                                     │ LiveKit Cloud     │
                                                     │ (SFU + dispatch)  │
                                                     └──────────────────┘
                                                              ▲
                                                              │ caller's mic
                                                       ┌──────┴───────┐
                                                       │  Caller      │
                                                       │  (browser)   │
                                                       └──────────────┘
```

The voice worker authenticates back to the API using the operator's bearer
token, embedded in the LiveKit participant metadata when the dashboard
mints the room token. On session start the worker POSTs a `Call` row
(status `active`), which the API broadcasts to every SSE subscriber so
the dashboard reflects the new call within a second. At session end the
worker POSTs again with the full transcript + tool-call timeline; the
same upsert flips the status to `completed` (or `escalated` if the LLM
called `escalate_to_human`).

---

## Quick start

You'll need: Docker, Node 18+, Python 3.12+.

```bash
# 1. Infrastructure
cp .env.example .env
# fill in: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET,
#         DEEPGRAM_API_KEY, CARTESIA_API_KEY, GROQ_API_KEY
docker compose up -d   # Postgres, Qdrant, MinIO

# 2. API
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
( cd apps/api && PYTHONPATH=. alembic upgrade head )
( cd apps/api && PYTHONPATH=. uvicorn app.main:app --reload )

# 3. Voice worker (separate venv — it's heavy)
( cd apps/voice-agent
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  python -m app.agent download-files
  python -m app.agent dev )

# 4. Web
npm install
npm --prefix apps/web run dev
```

Open **http://localhost:3000**. Sign in with the seeded admin shown on
the login screen, create a workspace, configure an agent, upload a doc to
Knowledge, and click "Start call" on the Agent page.

---

## Repository layout

```
apps/
  api/                FastAPI service · routes for auth, workspaces,
                      agents, knowledge, tools, calls, events (SSE),
                      analytics, livekit token. SQLAlchemy 2.0 +
                      Alembic migrations.
  voice-agent/        LiveKit Agents worker · per-call dynamic tool
                      registration, KB-grounded answers, transcript
                      capture, escalation.
  web/                Next.js 14 App Router · dark Linear/Vercel-style
                      dashboard. Workspace switcher, Live, Calls,
                      Agent, Knowledge, Tools, Analytics.

packages/             Reserved.
infra/                Local data volumes.
docker-compose.yml    Postgres · Qdrant · MinIO.
.env.example          Full env contract.
```

---

## What's not in V1

These are intentional cuts, not bugs:

- **Real phone calls** — LiveKit-only for now; SIP trunk for inbound PSTN
  would slot under the same worker.
- **Multi-clinic / multi-region** — Single-process API. Pub/sub is
  in-memory; we'll move to Redis when we need to.
- **Recording playback** — The MinIO container is up but recording
  upload/storage isn't wired yet.
- **HIPAA / SOC 2** — Development-grade. Production deployments would
  need encryption-at-rest configuration, audit logging, and a real auth
  story (JWT or sessions instead of in-memory bearer tokens).

---

## License

Source-available for reading and reference. Not yet open-source licensed
for production redistribution.
