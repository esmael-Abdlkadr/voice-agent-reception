# Local Setup

## Requirements

- Node.js 20+
- npm 10+
- Python 3.11+
- Docker Desktop or Docker Engine

## Start Infrastructure

```bash
cp .env.example .env
docker compose up -d
```

Services:

```text
Postgres: localhost:5432
Qdrant: localhost:6333
MinIO: localhost:9000
```

## Start API

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload
```

The API defaults to Postgres:

```text
VOICE_AGENT_STORAGE=postgres
DATABASE_URL=postgresql://voice_agent:voice_agent@localhost:5432/voice_agent_demo
GROQ_API_KEY=your-groq-key
```

API health check:

```bash
curl http://localhost:8000/health
```

## Start Web

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.
