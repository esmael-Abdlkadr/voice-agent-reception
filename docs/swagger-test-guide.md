# Swagger Test Guide

Open Swagger at `/docs` on the running API server.

## Authenticate First

1. Open `POST /auth/login`.
2. Use:

```json
{
  "email": "admin@voiceagent.local",
  "password": "admin123"
}
```

3. Copy `access_token` from the response.
4. Click `Authorize` in Swagger.
5. Enter:

```text
Bearer paste-access-token-here
```

Roles:

```text
platform_admin: full platform access and user management
campaign_operator: operational writes, no platform admin deletes or user management
analyst: read-focused role for future UI surfaces
```

## Suggested Order

1. `POST /auth/login`
2. `GET /auth/me`
3. `GET /users`
4. `POST /users`
5. `PATCH /users/{user_id}`
6. `GET /health`
7. `GET /contacts`
8. `POST /contacts`
9. `GET /contacts/{contact_id}`
10. `PATCH /contacts/{contact_id}`
11. `POST /appointments`
12. `PATCH /appointments/{appointment_id}`
13. `POST /agent/session`
14. `POST /agent/message`
15. `GET /calls`
16. `PATCH /calls/{call_id}`
17. `POST /knowledge/documents`
18. `POST /knowledge/search`
19. `POST /knowledge/answer`
20. `GET /llm/health`
21. `GET /llm/models`
22. `POST /llm/chat`
23. `POST /campaigns`
24. `POST /campaigns/{campaign_id}/import-csv`
25. `POST /campaigns/{campaign_id}/start-simulation`
26. `GET /analytics/overview`
27. `POST /sip/trunks`
28. `POST /sip/outbound-call`
29. `PUT /amd/settings`
30. `POST /amd/analyze`
31. `POST /voicemail/templates`
32. `POST /agent-profiles`
33. `PUT /orchestration/config`
34. `POST /recordings`
35. `PUT /settings/runtime`
36. `POST /costs/estimate`

## Useful Payloads

Create user:

```json
{
  "email": "operator@voiceagent.local",
  "name": "Operator",
  "role": "campaign_operator",
  "password": "operator123",
  "status": "active"
}
```

Create contact:

```json
{
  "name": "Maya Patel",
  "phone": "555-2200",
  "email": "maya@example.com",
  "company": "BrightCare Dental",
  "source": "swagger"
}
```

Create appointment:

```json
{
  "contact_id": "contact_0001",
  "contact_name": "Amara Johnson",
  "title": "Dental cleaning",
  "starts_at": "Tuesday 10:00 AM",
  "status": "booked",
  "notes": "Booked from Swagger"
}
```

Agent message:

```json
{
  "session_id": "use-session-id-from-agent-session",
  "message": "Hi, I am Lina. I need teeth cleaning next Tuesday morning. My phone is 555-0100."
}
```

Knowledge document:

```json
{
  "title": "Implant Financing Guide",
  "source_name": "swagger",
  "content": "Dental implant financing is available with monthly payment plans and no-interest options."
}
```

Knowledge answer:

```json
{
  "query": "Do you offer emergency appointments?",
  "max_context_items": 2
}
```

Direct LLM chat:

```json
{
  "message": "Answer as a dental receptionist: do you offer emergency appointments?",
  "system_prompt": "You are Ava, a concise AI voice assistant for BrightCare Dental.",
  "model": "llama-3.1-8b-instant"
}
```

Campaign CSV import:

```json
{
  "csv_content": "name,phone,email,company\nAri Caller,555-7777,ari@example.com,BrightCare Dental\n"
}
```

SIP trunk:

```json
{
  "name": "Local SIP Lab",
  "provider": "local-asterisk",
  "host": "sip.local",
  "username": "voice-agent",
  "caller_id": "+15550000000",
  "max_concurrent_calls": 3,
  "status": "draft"
}
```

AMD analysis:

```json
{
  "greeting_text": "Please leave a message after the tone.",
  "audio_duration_seconds": 8
}
```

Voicemail template:

```json
{
  "name": "Whitening Callback",
  "message_text": "Hi, this is BrightCare Dental calling about your whitening consultation.",
  "voice": "piper:en_US-lessac",
  "audio_url": "",
  "status": "draft"
}
```

Agent profile:

```json
{
  "name": "Receptionist Ava",
  "persona": "Warm and concise dental receptionist",
  "system_prompt": "Book appointments and answer BrightCare questions.",
  "voice": "browser-default",
  "language": "en-US",
  "temperature": 0.3,
  "status": "draft"
}
```

Runtime settings:

```json
{
  "llm_provider": "groq",
  "llm_model": "llama-3.1-8b-instant",
  "groq_base_url": "https://api.groq.com/openai/v1",
  "stt_provider": "faster-whisper",
  "tts_provider": "piper",
  "telephony_mode": "sip"
}
```

Cost estimate:

```json
{
  "daily_calls": 2000,
  "average_call_minutes": 2.5,
  "live_answer_rate": 0.35,
  "sip_cost_per_minute": 0.01,
  "ai_cost_per_live_minute": 0,
  "voicemail_cost_per_minute": 0
}
```
