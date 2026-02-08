"""
config.py — Application Configuration (Environment Variables)
=============================================================

Uses pydantic-settings to load environment variables from a `.env` file
and expose them as typed Python attributes. This centralises all config
in one place so the rest of the app just imports `settings`.

Environment variables loaded:
    SUPABASE_URL      → Supabase project URL (e.g. https://xxx.supabase.co)
    SUPABASE_KEY      → Supabase anon/public API key
    OPENAI_API_KEY    → OpenAI key for the LangChain ChatOpenAI LLM
    TAVILY_API_KEY    → Tavily search API key (optional, agent still works without it)
    MCP_SERVER_URL    → Google Trends MCP server endpoint (uses Docker service name in prod)
    FRONTEND_URL      → Frontend origin for CORS (e.g. http://localhost:5173)
    APP_NAME          → Display name for the FastAPI app (shows in /docs)
    DEBUG             → Debug flag (not used yet, reserved for future logging levels)
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and/or `.env` file.

    Pydantic-settings automatically:
      - Reads matching env vars (case-insensitive)
      - Falls back to `.env` file if the env var isn't set in the OS
      - Validates types (str, bool, etc.)
    """

    # ── Supabase ────────────────────────────────────────────────────────────
    # Used for authentication (signup/login) and database operations (messages table).
    SUPABASE_URL: str = ""   # e.g. "https://ityljtxeontmzfszfrii.supabase.co"
    SUPABASE_KEY: str = ""   # Supabase anon/public key (safe to use on client side)

    # ── OpenAI ──────────────────────────────────────────────────────────────
    # Powers the LangChain ReAct agent. Required for the chat to work.
    OPENAI_API_KEY: str = ""

    # ── Tavily ──────────────────────────────────────────────────────────────
    # Web search tool for the ReAct agent. Optional — agent works without it
    # but cannot search the web.
    TAVILY_API_KEY: str = ""

    # ── Google Trends MCP Server ────────────────────────────────────────────
    # URL of the MCP server that provides Google Trends/News tools.
    # In Docker Compose, this uses the service name (e.g. http://google-trends-mcp:8080/mcp/)
    # In local dev, use http://localhost:8080/mcp/
    MCP_SERVER_URL: str = "http://google-trends-mcp:8080/mcp"

    # ── CORS ────────────────────────────────────────────────────────────────
    # The frontend origin URL. Used to configure CORS so the browser allows
    # cross-origin requests from the React app to this FastAPI backend.
    FRONTEND_URL: str = "http://localhost:5173"

    # ── App Metadata ────────────────────────────────────────────────────────
    APP_NAME: str = "AI Chat Agent Backend"  # Shows in FastAPI /docs page title
    DEBUG: bool = False                       # Reserved for future verbose logging

    # ── Pydantic-settings config ────────────────────────────────────────────
    # Tells pydantic-settings to look for a `.env` file in the current
    # working directory (the backend/ folder when running uvicorn).
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


# Singleton instance — import this everywhere:
#   from app.core.config import settings
settings = Settings()
