import os

os.environ["VOICE_AGENT_STORAGE"] = "memory"

from fastapi.testclient import TestClient

from app.main import app
from app.services.store import reset_store, seed_store
from app.services import store


def client():
    reset_store()
    seed_store()
    return TestClient(app)


def auth_headers(api: TestClient, email: str = "admin@voiceagent.local", password: str = "admin123") -> dict[str, str]:
    token = api.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_reports_ok():
    response = client().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "voice-agent-api"}


def test_openapi_exposes_all_swagger_test_endpoints():
    paths = client().get("/openapi.json").json()["paths"]

    expected = {
        "/health",
        "/contacts",
        "/contacts/{contact_id}",
        "/appointments",
        "/appointments/{appointment_id}",
        "/campaigns",
        "/campaigns/{campaign_id}",
        "/campaigns/{campaign_id}/import-csv",
        "/campaigns/{campaign_id}/start-simulation",
        "/calls",
        "/calls/{call_id}",
        "/agent/session",
        "/agent/message",
        "/knowledge/documents",
        "/knowledge/documents/{document_id}",
        "/knowledge/search",
        "/knowledge/answer",
        "/analytics/overview",
        "/llm/health",
        "/llm/models",
        "/llm/chat",
        "/sip/trunks",
        "/sip/trunks/{trunk_id}",
        "/sip/outbound-call",
        "/amd/settings",
        "/amd/analyze",
        "/voicemail/templates",
        "/voicemail/templates/{template_id}",
        "/agent-profiles",
        "/agent-profiles/{profile_id}",
        "/orchestration/config",
        "/recordings",
        "/recordings/{recording_id}",
        "/settings/runtime",
        "/twilio/setup",
        "/twilio/voice/inbound",
        "/twilio/voice/gather",
        "/twilio/voice/status",
        "/twilio/voice/recording",
        "/costs/estimate",
        "/auth/login",
        "/auth/me",
        "/users",
        "/users/{user_id}",
    }

    assert expected.issubset(paths.keys())


def test_login_returns_token_and_current_user():
    api = client()
    headers = auth_headers(api)

    me = api.get("/auth/me", headers=headers)

    assert me.status_code == 200
    assert me.json()["role"] == "platform_admin"


def test_protected_write_requires_authentication():
    api = client()

    response = api.post("/contacts", json={"name": "No Auth"})

    assert response.status_code == 401


def test_operator_can_read_but_cannot_delete_or_manage_users():
    api = client()
    admin_headers = auth_headers(api)
    operator = api.post(
        "/users",
        json={"email": "operator@voiceagent.local", "name": "Operator", "role": "campaign_operator", "password": "operator123"},
        headers=admin_headers,
    ).json()
    operator_headers = auth_headers(api, "operator@voiceagent.local", "operator123")

    read_contacts = api.get("/contacts", headers=operator_headers)
    delete_contact = api.delete(f"/contacts/{api.get('/contacts', headers=operator_headers).json()[0]['id']}", headers=operator_headers)
    create_user = api.post(
        "/users",
        json={"email": "new@voiceagent.local", "name": "New", "role": "analyst", "password": "new123"},
        headers=operator_headers,
    )

    assert operator["role"] == "campaign_operator"
    assert read_contacts.status_code == 200
    assert delete_contact.status_code == 403
    assert create_user.status_code == 403


def test_admin_can_manage_users_and_delete_contacts():
    api = client()
    headers = auth_headers(api)
    contact = api.post("/contacts", json={"name": "Delete With Auth"}, headers=headers).json()
    user = api.post(
        "/users",
        json={"email": "viewer@voiceagent.local", "name": "Viewer", "role": "analyst", "password": "viewer123"},
        headers=headers,
    ).json()

    deleted_contact = api.delete(f"/contacts/{contact['id']}", headers=headers)
    updated_user = api.patch(f"/users/{user['id']}", json={"role": "campaign_operator"}, headers=headers)

    assert deleted_contact.status_code == 204
    assert updated_user.json()["role"] == "campaign_operator"


def test_contacts_can_be_created_and_listed():
    api = client()

    headers = auth_headers(api)
    created = api.post(
        "/contacts",
        json={
            "name": "Maya Patel",
            "phone": "+15551234567",
            "email": "maya@example.com",
            "company": "BrightCare Dental",
            "source": "referral",
        },
        headers=headers,
    )

    assert created.status_code == 201
    contacts = api.get("/contacts").json()
    assert any(contact["name"] == "Maya Patel" for contact in contacts)


def test_contact_can_be_read_updated_and_deleted():
    api = client()
    headers = auth_headers(api)
    created = api.post("/contacts", json={"name": "Edit Me", "phone": "555-1010"}, headers=headers).json()

    fetched = api.get(f"/contacts/{created['id']}", headers=headers)
    updated = api.patch(f"/contacts/{created['id']}", json={"email": "edited@example.com", "source": "swagger"}, headers=headers)
    deleted = api.delete(f"/contacts/{created['id']}", headers=headers)

    assert fetched.status_code == 200
    assert updated.json()["email"] == "edited@example.com"
    assert deleted.status_code == 204
    assert api.get(f"/contacts/{created['id']}", headers=headers).status_code == 404


def test_appointments_can_be_read_updated_and_deleted():
    api = client()
    headers = auth_headers(api)
    contact = api.get("/contacts").json()[0]
    created = api.post(
        "/appointments",
        json={
            "contact_id": contact["id"],
            "contact_name": contact["name"],
            "title": "Cleaning",
            "starts_at": "Monday 9:00 AM",
        },
        headers=headers,
    ).json()

    fetched = api.get(f"/appointments/{created['id']}")
    updated = api.patch(f"/appointments/{created['id']}", json={"status": "cancelled", "notes": "Patient requested reschedule."}, headers=headers)
    deleted = api.delete(f"/appointments/{created['id']}", headers=headers)

    assert fetched.status_code == 200
    assert updated.json()["status"] == "cancelled"
    assert deleted.status_code == 204
    assert api.get(f"/appointments/{created['id']}").status_code == 404


def test_agent_books_appointment_and_logs_transcript():
    api = client()
    headers = auth_headers(api)

    session = api.post("/agent/session", json={"direction": "inbound"}, headers=headers).json()
    reply = api.post(
        "/agent/message",
        json={
            "session_id": session["id"],
            "message": "Hi, I am Lina. I need teeth cleaning next Tuesday morning. My phone is 555-0100.",
        },
        headers=headers,
    )

    assert reply.status_code == 200
    body = reply.json()
    assert body["outcome"] == "appointment_booked"
    assert "Tuesday" in body["reply"]
    assert body["llm"]["mode"] in {"deterministic", "groq", "unavailable"}

    appointments = api.get("/appointments").json()
    calls = api.get("/calls").json()
    assert any(item["contact_name"] == "Lina" for item in appointments)
    assert any(call["id"] == session["id"] and call["outcome"] == "appointment_booked" for call in calls)


def test_knowledge_search_returns_seeded_faq():
    api = client()

    response = api.post("/knowledge/search", json={"query": "How much is whitening?"})

    assert response.status_code == 200
    assert response.json()["results"][0]["title"] == "BrightCare Dental FAQ"
    assert "whitening" in response.json()["results"][0]["content"].lower()


def test_knowledge_answer_returns_llm_answer_and_context():
    api = client()

    response = api.post("/knowledge/answer", json={"query": "What are your whitening prices?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "What are your whitening prices?"
    assert payload["answer"]
    assert payload["llm"]["mode"] in {"deterministic", "groq", "unavailable"}
    assert payload["results"]


def test_llm_health_reports_runtime_status():
    api = client()
    headers = auth_headers(api)

    response = api.get("/llm/health", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "groq"
    assert payload["model"] == "llama-3.1-8b-instant"
    assert payload["deterministic_mode"] is True
    assert payload["mode"] in {"deterministic", "groq", "unavailable"}


def test_llm_models_and_chat_endpoints_are_available():
    api = client()
    headers = auth_headers(api)

    models = api.get("/llm/models", headers=headers)
    chat = api.post("/llm/chat", json={"message": "Say hello in one short sentence."}, headers=headers)

    assert models.status_code == 200
    assert "models" in models.json()
    assert chat.status_code == 200
    assert chat.json()["reply"]
    assert chat.json()["llm"]["mode"] in {"deterministic", "groq", "unavailable"}


def test_campaign_simulation_creates_call_outcomes():
    api = client()
    headers = auth_headers(api)
    campaign = api.post("/campaigns", json={"name": "Whitening Follow-up", "mode": "outbound"}, headers=headers).json()

    response = api.post(f"/campaigns/{campaign['id']}/start-simulation", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["created_calls"] >= 2
    assert "appointment_booked" in payload["outcomes"]


def test_campaign_can_import_csv_and_be_updated():
    api = client()
    headers = auth_headers(api)
    campaign = api.post("/campaigns", json={"name": "Implant Leads", "mode": "outbound"}, headers=headers).json()

    imported = api.post(
        f"/campaigns/{campaign['id']}/import-csv",
        json={
            "csv_content": "name,phone,email,company\nAri Caller,555-7777,ari@example.com,BrightCare Dental\n",
        },
        headers=headers,
    )
    updated = api.patch(f"/campaigns/{campaign['id']}", json={"status": "paused", "prompt": "Offer implant consults."}, headers=headers)

    assert imported.status_code == 200
    assert imported.json()["imported"] == 1
    assert updated.json()["status"] == "paused"
    assert any(contact["name"] == "Ari Caller" for contact in api.get("/contacts").json())


def test_call_outcome_can_be_updated_from_swagger():
    api = client()
    headers = auth_headers(api)
    session = api.post("/agent/session", json={"direction": "inbound"}, headers=headers).json()

    updated = api.patch(f"/calls/{session['id']}", json={"outcome": "callback_requested", "summary": "Caller wants a callback."}, headers=headers)

    assert updated.status_code == 200
    assert updated.json()["outcome"] == "callback_requested"
    assert updated.json()["summary"] == "Caller wants a callback."


def test_agent_message_returns_404_for_missing_session():
    api = client()
    headers = auth_headers(api)

    response = api.post("/agent/message", json={"session_id": "call_missing", "message": "Hello"}, headers=headers)

    assert response.status_code == 404


def test_dashboard_metrics_summarize_platform_value():
    api = client()
    headers = auth_headers(api)
    session = api.post("/agent/session", json={"direction": "inbound"}, headers=headers).json()
    api.post(
        "/agent/message",
        json={
            "session_id": session["id"],
            "message": "This is Noah. I want whitening on Friday. Call me at 555-0199.",
        },
        headers=headers,
    )

    metrics = api.get("/analytics/overview").json()

    assert metrics["estimated_local_platform_cost"] == "$0"
    assert metrics["appointments_booked"] >= 1
    assert metrics["total_calls"] >= 1


def test_default_database_url_points_to_postgres():
    assert store.default_database_url().startswith("postgresql://")


def test_contacts_persist_after_store_reload():
    store.configure_storage("memory://v2-contact-test")
    api = client()
    headers = auth_headers(api)

    created = api.post(
        "/contacts",
        json={
            "name": "Persisted Patient",
            "phone": "555-0200",
            "email": "persisted@example.com",
            "company": "BrightCare Dental",
            "source": "v2-test",
        },
        headers=headers,
    ).json()

    store.reload_store()

    contacts = api.get("/contacts").json()
    assert any(contact["id"] == created["id"] and contact["name"] == "Persisted Patient" for contact in contacts)


def test_uploaded_knowledge_document_is_chunked_and_ranked_first(tmp_path):
    store.configure_storage("memory://v2-rag-test")
    api = client()
    headers = auth_headers(api)

    created = api.post(
        "/knowledge/documents",
        json={
            "title": "Implant Financing Guide",
            "source_name": "upload",
            "content": "Dental implant financing is available with monthly payment plans and no-interest options.",
        },
        headers=headers,
    )

    assert created.status_code == 201
    search = api.post("/knowledge/search", json={"query": "implant payment plans"}).json()

    assert search["results"][0]["title"] == "Implant Financing Guide"
    assert search["results"][0]["score"] > 0
    assert "implant" in search["results"][0]["matched_terms"]


def test_knowledge_document_can_be_read_and_deleted():
    api = client()
    headers = auth_headers(api)
    created = api.post(
        "/knowledge/documents",
        json={"title": "Sedation FAQ", "source_name": "swagger", "content": "Sedation is available for anxious patients."},
        headers=headers,
    ).json()

    fetched = api.get(f"/knowledge/documents/{created['id']}")
    deleted = api.delete(f"/knowledge/documents/{created['id']}", headers=headers)

    assert fetched.status_code == 200
    assert deleted.status_code == 204
    assert api.get(f"/knowledge/documents/{created['id']}").status_code == 404


def test_sip_trunk_and_outbound_call_request_are_swagger_ready():
    api = client()
    headers = auth_headers(api)
    trunk = api.post(
        "/sip/trunks",
        json={
            "name": "Local SIP Lab",
            "provider": "local-asterisk",
            "host": "sip.local",
            "username": "voice-agent",
            "caller_id": "+15550000000",
            "max_concurrent_calls": 3,
        },
        headers=headers,
    ).json()

    updated = api.patch(f"/sip/trunks/{trunk['id']}", json={"status": "active", "max_concurrent_calls": 5}, headers=headers).json()
    call = api.post(
        "/sip/outbound-call",
        json={"trunk_id": trunk["id"], "contact_id": api.get("/contacts").json()[0]["id"], "campaign_id": None},
        headers=headers,
    ).json()

    assert updated["status"] == "active"
    assert call["direction"] == "outbound"
    assert call["status"] == "queued"


def test_twilio_inbound_returns_twiml_and_creates_call_session():
    api = client()

    response = api.post(
        "/twilio/voice/inbound",
        data={"CallSid": "CA_TEST_INBOUND", "From": "+15550101010", "To": "+15550999999", "CallStatus": "ringing"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Gather" in response.text
    calls = api.get("/calls").json()
    twilio_call = next(call for call in calls if call["external_call_id"] == "CA_TEST_INBOUND")
    assert twilio_call["provider"] == "twilio"
    assert twilio_call["caller_number"] == "+15550101010"
    assert twilio_call["called_number"] == "+15550999999"


def test_twilio_gather_logs_transcript_and_creates_appointment_request():
    api = client()
    api.post(
        "/twilio/voice/inbound",
        data={"CallSid": "CA_TEST_GATHER", "From": "+15550101011", "To": "+15550999999", "CallStatus": "in-progress"},
    )

    response = api.post(
        "/twilio/voice/gather",
        data={
            "CallSid": "CA_TEST_GATHER",
            "From": "+15550101011",
            "To": "+15550999999",
            "CallStatus": "in-progress",
            "SpeechResult": "This is Maya. I need a cleaning next Tuesday morning.",
        },
    )

    assert response.status_code == 200
    assert "appointment request" in response.text
    calls = api.get("/calls").json()
    twilio_call = next(call for call in calls if call["external_call_id"] == "CA_TEST_GATHER")
    assert twilio_call["outcome"] == "appointment_requested"
    assert any(message["role"] == "user" and "Maya" in message["content"] for message in twilio_call["messages"])
    appointments = api.get("/appointments").json()
    request = next(item for item in appointments if item["contact_name"] == "Maya")
    assert request["status"] == "requested"
    assert "Staff should confirm" in request["notes"]


def test_twilio_status_callback_updates_call_duration():
    api = client()
    api.post(
        "/twilio/voice/inbound",
        data={"CallSid": "CA_TEST_STATUS", "From": "+15550101012", "To": "+15550999999", "CallStatus": "in-progress"},
    )

    response = api.post(
        "/twilio/voice/status",
        data={"CallSid": "CA_TEST_STATUS", "CallStatus": "completed", "CallDuration": "47"},
    )

    assert response.status_code == 200
    call = next(item for item in api.get("/calls").json() if item["external_call_id"] == "CA_TEST_STATUS")
    assert call["status"] == "completed"
    assert call["provider_status"] == "completed"
    assert call["duration_seconds"] == 47


def test_twilio_signature_validation_can_reject_missing_signature(monkeypatch):
    monkeypatch.setenv("TWILIO_VALIDATE_WEBHOOKS", "true")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "test-token")
    api = client()

    response = api.post(
        "/twilio/voice/inbound",
        data={"CallSid": "CA_TEST_SIGNATURE", "From": "+15550101013", "To": "+15550999999"},
    )

    assert response.status_code == 403


def test_twilio_setup_status_does_not_expose_secrets(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret-token")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+15550999999")
    monkeypatch.setenv("PUBLIC_WEBHOOK_BASE_URL", "https://voiceagent.ngrok.app")
    api = client()

    response = api.get("/twilio/setup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["account_sid_configured"] is True
    assert payload["auth_token_configured"] is True
    assert payload["phone_number_configured"] is True
    assert payload["inbound_webhook_url"] == "https://voiceagent.ngrok.app/twilio/voice/inbound"
    assert "secret-token" not in str(payload)


def test_amd_settings_and_analysis_are_available():
    api = client()
    headers = auth_headers(api)

    settings = api.put("/amd/settings", json={"enabled": True, "detection_window_seconds": 4, "sensitivity": 0.72}, headers=headers).json()
    voicemail = api.post("/amd/analyze", json={"greeting_text": "Please leave a message after the tone.", "audio_duration_seconds": 8}, headers=headers).json()
    live = api.post("/amd/analyze", json={"greeting_text": "Hello, this is Maya.", "audio_duration_seconds": 2}, headers=headers).json()

    assert settings["enabled"] is True
    assert voicemail["result"] == "voicemail"
    assert live["result"] == "live_person"


def test_voicemail_templates_can_be_managed():
    api = client()
    headers = auth_headers(api)
    template = api.post(
        "/voicemail/templates",
        json={
            "name": "Whitening Callback",
            "message_text": "Hi, this is BrightCare Dental calling about your whitening consultation.",
            "voice": "piper:en_US-lessac",
        },
        headers=headers,
    ).json()

    updated = api.patch(f"/voicemail/templates/{template['id']}", json={"status": "active"}, headers=headers).json()
    deleted = api.delete(f"/voicemail/templates/{template['id']}", headers=headers)

    assert updated["status"] == "active"
    assert deleted.status_code == 204


def test_agent_profiles_and_orchestration_config_are_available():
    api = client()
    headers = auth_headers(api)
    profile = api.post(
        "/agent-profiles",
        json={
            "name": "Receptionist Ava",
            "persona": "Warm and concise dental receptionist",
            "system_prompt": "Book appointments and answer BrightCare questions.",
            "voice": "browser-default",
            "language": "en-US",
        },
        headers=headers,
    ).json()

    updated_profile = api.patch(f"/agent-profiles/{profile['id']}", json={"temperature": 0.2, "status": "active"}, headers=headers).json()
    orchestration = api.put(
        "/orchestration/config",
        json={"framework": "pipecat", "transport": "browser", "vad_enabled": True, "barge_in_enabled": True},
        headers=headers,
    ).json()

    assert updated_profile["status"] == "active"
    assert orchestration["framework"] == "pipecat"


def test_recordings_runtime_settings_and_cost_estimate_are_available():
    api = client()
    headers = auth_headers(api)
    session = api.post("/agent/session", json={"direction": "inbound"}, headers=headers).json()
    recording = api.post(
        "/recordings",
        json={
            "call_id": session["id"],
            "storage_url": "minio://recordings/call.wav",
            "duration_seconds": 42,
            "transcript_status": "ready",
        },
        headers=headers,
    ).json()
    runtime = api.put(
        "/settings/runtime",
        json={
            "llm_provider": "groq",
            "llm_model": "llama-3.1-8b-instant",
            "groq_base_url": "https://api.groq.com/openai/v1",
            "stt_provider": "faster-whisper",
            "tts_provider": "piper",
            "telephony_mode": "sip",
        },
        headers=headers,
    ).json()
    estimate = api.post(
        "/costs/estimate",
        json={"daily_calls": 2000, "average_call_minutes": 2.5, "live_answer_rate": 0.35, "sip_cost_per_minute": 0.01},
        headers=headers,
    ).json()

    assert api.get(f"/recordings/{recording['id']}").json()["call_id"] == session["id"]
    assert runtime["llm_provider"] == "groq"
    assert runtime["llm_model"] == "llama-3.1-8b-instant"
    assert estimate["estimated_daily_cost"] > 0
