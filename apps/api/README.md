# Voice Agent API

FastAPI backend for the AI voice agent platform. The app uses Postgres by default and exposes Swagger-ready APIs for calls, contacts, appointments, campaigns, agent profiles, SIP settings, AMD, voicemail templates, knowledge, recordings, runtime settings, analytics, and costs.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload
```
