from __future__ import annotations

import os
from datetime import datetime, timezone
from itertools import count
from typing import Protocol, TypeVar

from app.models import AgentProfile, Appointment, CallMessage, CallSession, Campaign, Contact, KnowledgeDocument, Recording, SipTrunk, User, VoicemailTemplate


T = TypeVar("T", Contact, Appointment, Campaign, CallSession, KnowledgeDocument, SipTrunk, VoicemailTemplate, AgentProfile, Recording, User)
_ids = count(1)


def default_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://voice_agent:voice_agent@localhost:5432/voice_agent_demo")


class PersistenceBackend(Protocol):
    def ensure_schema(self) -> None: ...
    def save(self, collection: str, record_id: str, payload: str) -> None: ...
    def delete(self, collection: str, record_id: str) -> None: ...
    def delete_collection(self, collection: str) -> None: ...
    def load_collection(self, collection: str) -> list[tuple[str, str]]: ...


class MemoryBackend:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, str]] = {}

    def ensure_schema(self) -> None:
        return None

    def save(self, collection: str, record_id: str, payload: str) -> None:
        self.records.setdefault(collection, {})[record_id] = payload

    def delete(self, collection: str, record_id: str) -> None:
        self.records.get(collection, {}).pop(record_id, None)

    def delete_collection(self, collection: str) -> None:
        self.records[collection] = {}

    def load_collection(self, collection: str) -> list[tuple[str, str]]:
        return sorted(self.records.get(collection, {}).items())


class PostgresBackend:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS voice_agent_records (
                        collection TEXT NOT NULL,
                        id TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        PRIMARY KEY (collection, id)
                    )
                    """
                )

    def save(self, collection: str, record_id: str, payload: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO voice_agent_records (collection, id, payload, updated_at)
                    VALUES (%s, %s, %s::jsonb, now())
                    ON CONFLICT (collection, id)
                    DO UPDATE SET payload = EXCLUDED.payload, updated_at = now()
                    """,
                    (collection, record_id, payload),
                )

    def delete_collection(self, collection: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM voice_agent_records WHERE collection = %s", (collection,))

    def delete(self, collection: str, record_id: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM voice_agent_records WHERE collection = %s AND id = %s", (collection, record_id))

    def load_collection(self, collection: str) -> list[tuple[str, str]]:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, payload::text FROM voice_agent_records WHERE collection = %s ORDER BY id", (collection,))
                return list(cursor.fetchall())

    def _connect(self):
        try:
            import psycopg
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install API dependencies with `pip install -r apps/api/requirements.txt` to use Postgres.") from exc
        return psycopg.connect(self.database_url)


class PersistedDict(dict[str, T]):
    def __init__(self, collection: str, model: type[T]):
        super().__init__()
        self.collection = collection
        self.model = model

    def __setitem__(self, key: str, value: T) -> None:
        super().__setitem__(key, value)
        _backend.save(self.collection, key, value.model_dump_json())

    def clear(self, persist: bool = True) -> None:  # type: ignore[override]
        super().clear()
        if persist:
            _backend.delete_collection(self.collection)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        _backend.delete(self.collection, key)

    def load_from_backend(self) -> None:
        super().clear()
        for record_id, payload in _backend.load_collection(self.collection):
            dict.__setitem__(self, record_id, self.model.model_validate_json(payload))


def _make_backend(target: str | None = None) -> PersistenceBackend:
    storage = target or os.getenv("VOICE_AGENT_STORAGE", "postgres")
    if storage.startswith("memory://") or storage == "memory":
        return MemoryBackend()
    if storage.startswith("postgresql://") or storage.startswith("postgres://"):
        return PostgresBackend(storage)
    if storage == "postgres":
        return PostgresBackend(default_database_url())
    raise ValueError(f"Unsupported storage target: {storage}")


_backend: PersistenceBackend = _make_backend()

contacts: PersistedDict[Contact] = PersistedDict("contacts", Contact)
appointments: PersistedDict[Appointment] = PersistedDict("appointments", Appointment)
campaigns: PersistedDict[Campaign] = PersistedDict("campaigns", Campaign)
calls: PersistedDict[CallSession] = PersistedDict("calls", CallSession)
knowledge_documents: PersistedDict[KnowledgeDocument] = PersistedDict("knowledge_documents", KnowledgeDocument)
sip_trunks: PersistedDict[SipTrunk] = PersistedDict("sip_trunks", SipTrunk)
voicemail_templates: PersistedDict[VoicemailTemplate] = PersistedDict("voicemail_templates", VoicemailTemplate)
agent_profiles: PersistedDict[AgentProfile] = PersistedDict("agent_profiles", AgentProfile)
recordings: PersistedDict[Recording] = PersistedDict("recordings", Recording)
users: PersistedDict[User] = PersistedDict("users", User)


def configure_storage(target: str | None = None) -> None:
    global _backend
    _backend = _make_backend(target)
    reload_store()


def reload_store() -> None:
    _backend.ensure_schema()
    for collection in _collections():
        collection.load_from_backend()
    _sync_id_counter()


def reset_store() -> None:
    global _ids
    _ids = count(1)
    for collection in _collections():
        collection.clear()


def next_id(prefix: str) -> str:
    return f"{prefix}_{next(_ids):04d}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_store() -> None:
    reload_store()
    _ensure_admin_user()
    amara = _ensure_contact(
        name="Amara Johnson",
        phone="555-0112",
        email="amara@example.com",
        company="BrightCare Dental",
        source="seed",
    )
    daniel = _ensure_contact(
        name="Daniel Reed",
        phone="555-0144",
        email="daniel@example.com",
        company="BrightCare Dental",
        source="seed",
    )
    _ensure_campaign("Whitening Follow-up", "outbound")
    _ensure_knowledge_document(
        title="BrightCare Dental FAQ",
        source_name="seed",
        content=(
            "BrightCare Dental is open Monday through Friday from 9:00 AM to 5:00 PM. "
            "Teeth whitening consultations start at $149. Emergency appointments are available "
            "for urgent pain, swelling, or broken teeth. First-time patients should bring ID, "
            "insurance details, and any recent dental records."
        ),
    )
    _ensure_starter_call(amara, "appointment_booked", "Amara booked a whitening consultation for Friday morning.")
    _ensure_starter_call(daniel, "callback_requested", "Daniel asked for a callback about emergency appointment availability.")
    _ensure_starter_appointment(amara)



def add_call_message(session: CallSession, role: str, content: str) -> CallMessage:
    message = CallMessage(id=next_id("message"), session_id=session.id, role=role, content=content, created_at=now_iso())
    session.messages.append(message)
    save_call(session)
    return message


def save_call(session: CallSession) -> None:
    calls[session.id] = session


def save_campaign(campaign: Campaign) -> None:
    campaigns[campaign.id] = campaign


def is_internal_qa_record(*values: object) -> bool:
    haystack = " ".join(str(value or "") for value in values).lower()
    return "curl" in haystack or "sip_0033" in haystack


def _collections() -> list[PersistedDict]:
    return [contacts, appointments, campaigns, calls, knowledge_documents, sip_trunks, voicemail_templates, agent_profiles, recordings, users]


def _ensure_admin_user() -> None:
    admin_hash = "sha256$240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
    for user in users.values():
        if user.email.lower() == "admin@voiceagent.local":
            if user.password_hash != admin_hash or user.role != "platform_admin" or user.status != "active":
                users[user.id] = user.model_copy(update={"password_hash": admin_hash, "role": "platform_admin", "status": "active"})
            return
    admin = User(
        id=next_id("user"),
        email="admin@voiceagent.local",
        name="Platform Admin",
        role="platform_admin",
        password_hash=admin_hash,
        status="active",
    )
    users[admin.id] = admin


def _ensure_contact(name: str, phone: str, email: str, company: str, source: str) -> Contact:
    for contact in contacts.values():
        if contact.name.lower() == name.lower():
            return contact
    contact = Contact(id=next_id("contact"), name=name, phone=phone, email=email, company=company, source=source)
    contacts[contact.id] = contact
    return contact


def _ensure_campaign(name: str, mode: str) -> Campaign:
    for campaign in campaigns.values():
        if campaign.name.lower() == name.lower():
            return campaign
    campaign = Campaign(id=next_id("campaign"), name=name, mode=mode, status="active")
    campaigns[campaign.id] = campaign
    return campaign


def _ensure_knowledge_document(title: str, source_name: str, content: str) -> KnowledgeDocument:
    for document in knowledge_documents.values():
        if document.title.lower() == title.lower():
            return document
    document = KnowledgeDocument(id=next_id("doc"), title=title, source_name=source_name, content=content)
    knowledge_documents[document.id] = document
    return document


def _ensure_starter_call(contact: Contact, outcome: str, summary: str) -> None:
    if any(call.contact_id == contact.id and call.summary == summary for call in calls.values()):
        return
    session = CallSession(
        id=next_id("call"),
        contact_id=contact.id,
        contact_name=contact.name,
        direction="inbound" if outcome == "appointment_booked" else "outbound",
        status="completed",
        outcome=outcome,
        summary=summary,
        started_at=now_iso(),
        ended_at=now_iso(),
    )
    calls[session.id] = session


def _ensure_starter_appointment(contact: Contact) -> None:
    if any(appointment.contact_id == contact.id and appointment.title == "Whitening consultation" for appointment in appointments.values()):
        return
    appointment = Appointment(
        id=next_id("appointment"),
        contact_id=contact.id,
        contact_name=contact.name,
        title="Whitening consultation",
        starts_at="Friday 10:00 AM",
        status="booked",
        notes="Booked by Ava after confirming the caller's preferred time.",
    )
    appointments[appointment.id] = appointment


def _sync_id_counter() -> None:
    global _ids
    max_id = 0
    for collection in _collections():
        for record_id in collection:
            try:
                max_id = max(max_id, int(record_id.rsplit("_", 1)[1]))
            except (IndexError, ValueError):
                continue
    _ids = count(max_id + 1)


if os.getenv("VOICE_AGENT_STORAGE") == "memory":
    reload_store()
