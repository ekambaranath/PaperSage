"""Central configuration for PaperSage, loaded from environment variables.

For local runs, values are read from a `.env` file if present. In GitHub
Actions they come from repository secrets / workflow env.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    """Minimal .env loader (no external dependency) for local development."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # Do not clobber values already present in the real environment.
        os.environ.setdefault(key, value)


_load_dotenv()


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)).strip())
    except (TypeError, ValueError):
        return default


DEFAULT_TOPICS = (
    "Agentic AI, AI agents, tool use, LLM reasoning, "
    "retrieval-augmented generation (RAG), multi-agent systems, new AI research"
)


@dataclass
class Config:
    openrouter_api_key: str = field(default_factory=lambda: _get("OPENROUTER_API_KEY"))
    gmail_address: str = field(default_factory=lambda: _get("GMAIL_ADDRESS"))
    gmail_app_password: str = field(default_factory=lambda: _get("GMAIL_APP_PASSWORD"))
    recipient_email: str = field(
        default_factory=lambda: _get("RECIPIENT_EMAIL") or _get("GMAIL_ADDRESS")
    )

    topics_raw: str = field(
        default_factory=lambda: _get("PAPERSAGE_TOPICS") or DEFAULT_TOPICS
    )

    summarizer_model: str = field(
        default_factory=lambda: _get("SUMMARIZER_MODEL") or "stealth/ox-alpha"
    )
    triage_model: str = field(
        default_factory=lambda: _get("TRIAGE_MODEL") or "google/gemini-2.5-flash"
    )

    lookback_days: int = field(default_factory=lambda: _get_int("LOOKBACK_DAYS", 2))
    max_papers: int = field(default_factory=lambda: _get_int("MAX_PAPERS", 10))
    # Cap on candidates fed to the triage model before ranking.
    max_candidates: int = field(default_factory=lambda: _get_int("MAX_CANDIDATES", 120))

    ncbi_api_key: str = field(default_factory=lambda: _get("NCBI_API_KEY"))
    semantic_scholar_api_key: str = field(
        default_factory=lambda: _get("SEMANTIC_SCHOLAR_API_KEY")
    )

    dry_run: bool = field(default_factory=lambda: _get("DRY_RUN", "0") in {"1", "true", "True"})

    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    @property
    def topics(self) -> list[str]:
        return [t.strip() for t in self.topics_raw.split(",") if t.strip()]

    def validate(self) -> list[str]:
        """Return a list of human-readable problems; empty means all good."""
        problems: list[str] = []
        if not self.openrouter_api_key:
            problems.append("OPENROUTER_API_KEY is not set.")
        if not self.dry_run:
            if not self.gmail_address:
                problems.append("GMAIL_ADDRESS is not set.")
            if not self.gmail_app_password:
                problems.append("GMAIL_APP_PASSWORD is not set.")
            if not self.recipient_email:
                problems.append("RECIPIENT_EMAIL is not set.")
        return problems


def load_config() -> Config:
    return Config()
