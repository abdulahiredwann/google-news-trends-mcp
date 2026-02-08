"""
main.py — FastAPI Application Entry Point
==========================================

This is the root of the backend application. It:
1. Creates the FastAPI app instance with a custom title.
2. Adds CORS middleware so the React frontend can make cross-origin requests.
3. Adds custom AuthMiddleware to protect all routes except public ones.
4. Registers all API routers (health, auth, chat).

Middleware execution order (per request):
    Request → CORS check → AuthMiddleware (JWT validation) → Router handler → Response
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.middleware.auth import AuthMiddleware
from app.routers import health, auth, chat

# ── Create FastAPI Application ──────────────────────────────────────────────
# The app title appears in the auto-generated OpenAPI docs at /docs
app = FastAPI(title=settings.APP_NAME)

# ── CORS Middleware ─────────────────────────────────────────────────────────
# Cross-Origin Resource Sharing: allows the React frontend (running on a
# different port/domain) to call this API. Without this, browsers block
# requests from the frontend to the backend.
#
# allow_origins: List of allowed frontend URLs
# allow_credentials: Allows cookies/auth headers to be sent
# allow_methods: All HTTP methods (GET, POST, PUT, DELETE, etc.)
# allow_headers: All headers (including Authorization with JWT)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth Middleware ─────────────────────────────────────────────────────────
# Custom middleware that intercepts every request, checks for a valid
# Supabase JWT token in the Authorization header, and attaches user_id,
# user_email, and access_token to request.state for downstream handlers.
# Public paths (login, signup, health, docs) are excluded from auth checks.
app.add_middleware(AuthMiddleware)

# ── Register API Routers ───────────────────────────────────────────────────
# Each router handles a group of related endpoints:
#   - health: GET /health → service health check
#   - auth:   POST /auth/signup, POST /auth/login → user authentication
#   - chat:   GET /chat/conversations, GET /chat/conversations/{id}/messages,
#             POST /chat/send → AI chat with SSE streaming
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
