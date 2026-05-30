"""Process-wide configuration. Loads the repo-root .env on import."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_local_env() -> None:
    for parent in [Path.cwd(), *Path.cwd().parents]:
        env_path = parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if not line or line.strip().startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return


_load_local_env()


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


@dataclass(frozen=True)
class Settings:
    database_url: str
    qdrant_url: str
    groq_api_key: str
    groq_base_url: str
    groq_chat_model: str
    embedding_model: str
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    seed_admin_email: str
    seed_admin_password: str
    service_api_key: str
    jwt_secret: str
    jwt_expire_hours: int


def get_settings() -> Settings:
    return Settings(
        database_url=_normalize_db_url(
            os.getenv(
                "DATABASE_URL",
                "postgresql://voice_agent:voice_agent@localhost:5432/voice_agent_demo",
            )
        ),
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        groq_chat_model=os.getenv("GROQ_CHAT_MODEL", "llama-3.1-8b-instant"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        livekit_url=os.getenv("LIVEKIT_URL", ""),
        livekit_api_key=os.getenv("LIVEKIT_API_KEY", ""),
        livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
        seed_admin_email=os.getenv("SEED_ADMIN_EMAIL", "admin@voiceops.dev"),
        seed_admin_password=os.getenv("SEED_ADMIN_PASSWORD", "voiceops-dev"),
        service_api_key=os.getenv("SERVICE_API_KEY", "dev-service-key-change-me"),
        jwt_secret=os.getenv("JWT_SECRET", "dev-jwt-secret-change-me"),
        jwt_expire_hours=int(os.getenv("JWT_EXPIRE_HOURS", "168")),
    )


settings = get_settings()
