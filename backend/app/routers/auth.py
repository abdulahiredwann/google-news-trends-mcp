"""
auth.py — Authentication Router (Signup & Login)
=================================================

Handles user registration and login via Supabase Auth.

Endpoints:
    POST /auth/signup → Create a new user account, return JWT + user info
    POST /auth/login  → Authenticate existing user, return JWT + user info

Both endpoints are PUBLIC (no JWT required) — they are listed in
PUBLIC_PATHS in middleware/auth.py.

Flow:
    1. Frontend sends { email, password } as JSON.
    2. Backend calls Supabase Auth API (sign_up or sign_in_with_password).
    3. Supabase returns a session object with access_token (JWT).
    4. Backend returns the token + user_id + email to the frontend.
    5. Frontend stores the token and sends it with every subsequent request.
"""

from fastapi import APIRouter, HTTPException
from app.schemas.auth import AuthRequest, AuthResponse
from app.core.config import settings
from supabase import create_client

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_supabase():
    """
    Create a Supabase client for auth operations.

    Returns:
        supabase.Client: A fresh Supabase client instance using the
        project URL and anon key from settings.

    Note:
        We create a new client per request to avoid shared state issues.
        This client uses the anon key (not a user token) because the
        user hasn't authenticated yet at this point.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


@router.post("/signup", response_model=AuthResponse)
async def signup(req: AuthRequest):
    """
    Create a new user account with email and password.

    Args:
        req (AuthRequest): JSON body with `email` (valid email) and `password` (string).

    Returns:
        AuthResponse: { access_token, user_id, email }

    Raises:
        HTTPException 400: If signup fails (e.g. email already exists, weak password).

    Flow:
        1. Call Supabase auth.sign_up() with email + password.
        2. If email confirmation is enabled, user gets an email (we return a message).
        3. If confirmation is disabled (dev mode), we get a session immediately.
        4. Return the JWT access_token so the frontend can start using it right away.
    """
    try:
        client = _get_supabase()
        result = client.auth.sign_up({
            "email": req.email,
            "password": req.password,
        })

        if result.user is None:
            raise HTTPException(status_code=400, detail="Signup failed")

        session = result.session
        if session is None:
            # Email confirmation is required — user must check their inbox
            raise HTTPException(
                status_code=200,
                detail="Check your email to confirm your account",
            )

        return AuthResponse(
            access_token=session.access_token,
            user_id=result.user.id,
            email=req.email,
        )

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Signup failed. Please try again.")


@router.post("/login", response_model=AuthResponse)
async def login(req: AuthRequest):
    """
    Log in with email and password.

    Args:
        req (AuthRequest): JSON body with `email` and `password`.

    Returns:
        AuthResponse: { access_token, user_id, email }

    Raises:
        HTTPException 401: If credentials are invalid (wrong email or password).

    Flow:
        1. Call Supabase auth.sign_in_with_password() with email + password.
        2. Supabase verifies credentials and returns a session with JWT.
        3. Return the JWT so the frontend can store it and use it for API calls.

    Security note:
        We intentionally return a generic "Invalid credentials" message for
        ALL failure cases to avoid leaking whether an email exists or not.
    """
    try:
        client = _get_supabase()
        result = client.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })

        if result.user is None or result.session is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return AuthResponse(
            access_token=result.session.access_token,
            user_id=result.user.id,
            email=req.email,
        )

    except HTTPException:
        raise
    except Exception as e:
        # Don't leak specific error details — always say "Invalid credentials"
        raise HTTPException(status_code=401, detail="Invalid credentials")
