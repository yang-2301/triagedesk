"""Application configuration via environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
try:
    DATA_DIR.mkdir(exist_ok=True)
except FileExistsError:  # some sandboxed environments raise despite exist_ok
    pass

DB_PATH = DATA_DIR / "triagedesk.db"
DATABASE_URL = os.environ.get("TRIAGEDESK_DB", f"sqlite:///{DB_PATH}")

SECRET_KEY = os.environ.get("TRIAGEDESK_SECRET", "dev-only-change-me")
ACCESS_TOKEN_TTL_MIN = int(os.environ.get("TRIAGEDESK_ACCESS_TTL", "30"))
REFRESH_TOKEN_TTL_DAYS = int(os.environ.get("TRIAGEDESK_REFRESH_TTL", "14"))

# Optional: when set, AI triage upgrades from the local NB classifier to an LLM.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL = os.environ.get("TRIAGEDESK_LLM_MODEL", "gpt-4o-mini")

# SLA response targets, in hours, keyed by ticket priority.
SLA_HOURS = {"urgent": 1, "high": 4, "normal": 24, "low": 72}
