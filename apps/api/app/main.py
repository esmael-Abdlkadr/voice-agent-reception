from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import agent, agent_profiles, amd, analytics, appointments, auth, calls, campaigns, contacts, costs, health, knowledge, livekit, llm, orchestration, recordings, settings, sip, twilio, users, voicemail
from app.services.store import seed_store


app = FastAPI(title="VoiceAgentOS Platform API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(contacts.router)
app.include_router(appointments.router)
app.include_router(calls.router)
app.include_router(campaigns.router)
app.include_router(knowledge.router)
app.include_router(agent.router)
app.include_router(analytics.router)
app.include_router(sip.router)
app.include_router(amd.router)
app.include_router(voicemail.router)
app.include_router(agent_profiles.router)
app.include_router(orchestration.router)
app.include_router(recordings.router)
app.include_router(settings.router)
app.include_router(costs.router)
app.include_router(llm.router)
app.include_router(twilio.router)
app.include_router(livekit.router)

seed_store()
