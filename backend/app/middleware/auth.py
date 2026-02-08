"""
auth.py — JWT Authentication Middleware
=======================================

This middleware runs on EVERY incoming request before it reaches a router.
It validates the Supabase JWT token and attaches user information to the
request so downstream handlers can use it.

Flow:
    1. Check if the path is public (login, signup, health, docs) → skip auth.
    2. Check if it's a CORS preflight (OPTIONS) → skip auth.
    3. Extract the Bearer token from the Authorization header.
    4. Call Supabase's /auth/v1/user endpoint to verify the token is valid.
    5. If valid → attach user_id, user_email, access_token to request.state.
    6. If invalid → return 401 Unauthorized immediately (request never reaches router).

This is the security gate — no unauthenticated request can reach /chat/* endpoints.

Note on CORS:
    When this middleware returns a 401 directly, the response bypasses the
    CORSMiddleware (which sits above it). So we must manually add CORS
    headers to our 401 responses, otherwise the browser blocks them and
    the frontend can't read the status code.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
import httpx


# ── Public Paths ────────────────────────────────────────────────────────────
# These routes do NOT require a JWT token. Everything else is protected.
PUBLIC_PATHS = {"/health", "/auth/login", "/auth/signup", "/docs", "/openapi.json"}

# ── Allowed CORS origins (must match main.py CORS config) ──────────────────
ALLOWED_ORIGINS = {settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"}


def _cors_response(status_code: int, content: dict, request: Request) -> JSONResponse:
    """
    Create a JSONResponse with CORS headers so the browser doesn't block it.

    When the auth middleware rejects a request (401), it returns a response
    BEFORE the CORSMiddleware has a chance to add headers. Without CORS
    headers, the browser blocks the response entirely and the frontend
    sees a network error instead of a clean 401.

    Args:
        status_code: HTTP status code (e.g. 401).
        content:     JSON body (e.g. {"detail": "..."}).
        request:     The incoming request (used to read the Origin header).

    Returns:
        JSONResponse with Access-Control-Allow-* headers if the origin is allowed.
    """
    response = JSONResponse(status_code=status_code, content=content)
    origin = request.headers.get("origin", "")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
    return response


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that validates Supabase JWT tokens.

    For every protected request, it:
    - Extracts the Bearer token from the Authorization header
    - Verifies it against Supabase's auth API
    - Attaches user info (user_id, user_email, access_token) to request.state
    - Returns 401 if the token is missing, invalid, or expired

    Usage in routers:
        user_id = request.state.user_id
        token   = request.state.access_token
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process each incoming HTTP request.

        Args:
            request:   The incoming HTTP request object.
            call_next: Async callable to pass the request to the next middleware/route.

        Returns:
            Response from the next handler (if auth passes) or a 401 JSONResponse.
        """

        # ── Step 1: Skip auth for public paths ─────────────────────────────
        # Login, signup, health check, and docs don't need authentication.
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # ── Step 2: Skip CORS preflight requests ───────────────────────────
        # Browsers send an OPTIONS request before the real request to check
        # if CORS is allowed. These must pass through without auth.
        if request.method == "OPTIONS":
            return await call_next(request)

        # ── Step 3: Extract Bearer token ───────────────────────────────────
        # Expected header format: "Authorization: Bearer <jwt_token>"
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return _cors_response(
                401,
                {"detail": "Missing or invalid Authorization header"},
                request,
            )

        token = auth_header.split(" ", 1)[1]

        # ── Step 4: Verify token with Supabase ─────────────────────────────
        # We call Supabase's /auth/v1/user endpoint with the JWT. If the
        # token is valid, Supabase returns the user object. If expired or
        # invalid, it returns a non-200 status.
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.SUPABASE_URL}/auth/v1/user",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "apikey": settings.SUPABASE_KEY,
                    },
                )

            if response.status_code != 200:
                return _cors_response(
                    401,
                    {"detail": "Invalid or expired token"},
                    request,
                )

            # ── Step 5: Attach user info to request.state ──────────────────
            # This makes user_id and access_token available in all route
            # handlers via request.state.user_id, request.state.access_token
            user_data = response.json()
            request.state.user_id = user_data["id"]
            request.state.user_email = user_data.get("email", "")
            request.state.access_token = token

        except Exception:
            # Network error, Supabase down, malformed response, etc.
            return _cors_response(
                401,
                {"detail": "Token verification failed"},
                request,
            )

        # ── Step 6: Continue to the actual route handler ───────────────────
        return await call_next(request)
