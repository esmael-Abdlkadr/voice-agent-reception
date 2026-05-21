from __future__ import annotations

import os
from pathlib import Path

from app.models import RuntimeSettings


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

_runtime = RuntimeSettings(
    llm_provider=os.getenv("LLM_PROVIDER", "groq"),
    llm_model=os.getenv("GROQ_CHAT_MODEL", "llama-3.1-8b-instant"),
    groq_base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
)


def get_runtime() -> RuntimeSettings:
    return _runtime


def update_runtime(settings: RuntimeSettings) -> RuntimeSettings:
    global _runtime
    _runtime = settings
    return _runtime
