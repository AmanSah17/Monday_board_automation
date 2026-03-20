"""
Configuration helpers for the monday.com automation project.
"""
import os

from dotenv import load_dotenv


load_dotenv()


MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN", "").strip()
MONDAY_API_VERSION = os.getenv("MONDAY_API_VERSION", "2026-01").strip()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_ROUTER_MODEL = os.getenv("OPENAI_ROUTER_MODEL", OPENAI_MODEL).strip()
OPENAI_REASONER_MODEL = os.getenv("OPENAI_REASONER_MODEL", OPENAI_MODEL).strip()
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "Monday.com-Board-Automation").strip()
LANGSMITH_API_KEY = (
    os.getenv("LANGSMITH_API_KEY", "").strip()
    or os.getenv("LANGCHAIN_API_KEY", "").strip()
)
LANGCHAIN_TRACING_ENABLED = os.getenv(
    "LANGCHAIN_TRACING_V2",
    "true" if LANGSMITH_API_KEY else "false",
).strip().lower() == "true"


def missing_setting_message(setting_name: str) -> str:
    """Return a consistent error message for required env vars."""
    return (
        f"Missing required setting '{setting_name}'. "
        f"Set it in your environment or .env file before calling this endpoint."
    )
