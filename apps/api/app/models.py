from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    company: str = ""
    source: str = "manual"


class Contact(ContactCreate):
    id: str


class ContactUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    company: str | None = None
    source: str | None = None


class AppointmentCreate(BaseModel):
    contact_id: str
    contact_name: str
    title: str
    starts_at: str
    status: str = "booked"
    notes: str = ""


class Appointment(AppointmentCreate):
    id: str


class AppointmentUpdate(BaseModel):
    contact_id: str | None = None
    contact_name: str | None = None
    title: str | None = None
    starts_at: str | None = None
    status: str | None = None
    notes: str | None = None


class CampaignCreate(BaseModel):
    name: str
    mode: str = "outbound"
    prompt: str = "Qualify interest and offer an appointment."


class Campaign(CampaignCreate):
    id: str
    status: str = "draft"


class CampaignUpdate(BaseModel):
    name: str | None = None
    mode: str | None = None
    prompt: str | None = None
    status: str | None = None


class CampaignCsvImport(BaseModel):
    csv_content: str


class CallMessage(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: str


class CallSession(BaseModel):
    id: str
    contact_id: str | None = None
    contact_name: str = "Unknown caller"
    campaign_id: str | None = None
    direction: str = "inbound"
    status: str = "active"
    outcome: str = "in_progress"
    summary: str = ""
    started_at: str
    ended_at: str | None = None
    provider: str = "browser"
    external_call_id: str = ""
    caller_number: str = ""
    called_number: str = ""
    provider_status: str = ""
    duration_seconds: int = 0
    last_webhook_at: str | None = None
    messages: list[CallMessage] = Field(default_factory=list)


class CallSessionUpdate(BaseModel):
    status: str | None = None
    outcome: str | None = None
    summary: str | None = None
    ended_at: str | None = None
    provider_status: str | None = None
    duration_seconds: int | None = None
    last_webhook_at: str | None = None


class KnowledgeDocumentCreate(BaseModel):
    title: str
    content: str
    source_name: str = "manual"


class KnowledgeDocument(KnowledgeDocumentCreate):
    id: str


class AgentSessionCreate(BaseModel):
    direction: str = "inbound"
    contact_id: str | None = None
    campaign_id: str | None = None


class AgentMessageCreate(BaseModel):
    session_id: str
    message: str


class KnowledgeSearchRequest(BaseModel):
    query: str


class KnowledgeAnswerRequest(BaseModel):
    query: str
    max_context_items: int = 2


class KnowledgeAnswerResponse(BaseModel):
    query: str
    answer: str
    llm: dict[str, str]
    results: list[dict]


class LlmHealthResponse(BaseModel):
    provider: str
    model: str
    deterministic_mode: bool
    api_key_configured: bool
    provider_reachable: bool
    model_available: bool
    mode: str


class LlmModelInfo(BaseModel):
    name: str
    size: int = 0
    modified_at: str = ""


class LlmModelsResponse(BaseModel):
    provider: str
    models: list[LlmModelInfo]


class LlmChatRequest(BaseModel):
    message: str
    system_prompt: str = "You are Ava, a concise AI voice assistant for BrightCare Dental."
    model: str | None = None


class LlmChatResponse(BaseModel):
    reply: str
    llm: dict[str, str]


class SipTrunkCreate(BaseModel):
    name: str
    provider: str
    host: str
    username: str = ""
    caller_id: str = ""
    max_concurrent_calls: int = 1
    status: str = "draft"


class SipTrunk(SipTrunkCreate):
    id: str


class SipTrunkUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    host: str | None = None
    username: str | None = None
    caller_id: str | None = None
    max_concurrent_calls: int | None = None
    status: str | None = None


class OutboundCallRequest(BaseModel):
    trunk_id: str
    contact_id: str
    campaign_id: str | None = None


class AmdSettings(BaseModel):
    enabled: bool = True
    detection_window_seconds: int = 4
    sensitivity: float = 0.7


class AmdAnalysisRequest(BaseModel):
    greeting_text: str = ""
    audio_duration_seconds: float = 0


class VoicemailTemplateCreate(BaseModel):
    name: str
    message_text: str
    voice: str = "browser-default"
    audio_url: str = ""
    status: str = "draft"


class VoicemailTemplate(VoicemailTemplateCreate):
    id: str


class VoicemailTemplateUpdate(BaseModel):
    name: str | None = None
    message_text: str | None = None
    voice: str | None = None
    audio_url: str | None = None
    status: str | None = None


class AgentProfileCreate(BaseModel):
    name: str
    persona: str
    system_prompt: str
    voice: str = "browser-default"
    language: str = "en-US"
    temperature: float = 0.3
    status: str = "draft"


class AgentProfile(AgentProfileCreate):
    id: str


class AgentProfileUpdate(BaseModel):
    name: str | None = None
    persona: str | None = None
    system_prompt: str | None = None
    voice: str | None = None
    language: str | None = None
    temperature: float | None = None
    status: str | None = None


class OrchestrationConfig(BaseModel):
    framework: str = "pipecat"
    transport: str = "browser"
    vad_enabled: bool = True
    barge_in_enabled: bool = True
    target_latency_ms: int = 900


class RecordingCreate(BaseModel):
    call_id: str
    storage_url: str
    duration_seconds: float
    transcript_status: str = "pending"


class Recording(RecordingCreate):
    id: str


class RuntimeSettings(BaseModel):
    llm_provider: str = "groq"
    llm_model: str = "llama-3.1-8b-instant"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    stt_provider: str = "faster-whisper"
    tts_provider: str = "piper"
    telephony_mode: str = "browser"


class TwilioSetupStatus(BaseModel):
    account_sid_configured: bool
    auth_token_configured: bool
    phone_number_configured: bool
    public_webhook_base_url: str
    validate_webhooks: bool
    inbound_webhook_url: str
    gather_webhook_url: str
    status_callback_url: str
    recording_callback_url: str


class CostEstimateRequest(BaseModel):
    daily_calls: int
    average_call_minutes: float
    live_answer_rate: float
    sip_cost_per_minute: float
    ai_cost_per_live_minute: float = 0
    voicemail_cost_per_minute: float = 0


class UserCreate(BaseModel):
    email: str
    name: str
    role: str = "analyst"
    password: str
    status: str = "active"


class User(BaseModel):
    id: str
    email: str
    name: str
    role: str
    password_hash: str
    status: str = "active"


class UserPublic(BaseModel):
    id: str
    email: str
    name: str
    role: str
    status: str = "active"


class UserUpdate(BaseModel):
    email: str | None = None
    name: str | None = None
    role: str | None = None
    password: str | None = None
    status: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
