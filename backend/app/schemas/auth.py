"""
auth.py — Authentication Pydantic Schemas
==========================================

Defines the request/response models for the authentication endpoints.
Pydantic validates incoming JSON bodies and serialises outgoing responses.

Models:
    AuthRequest   → Input for POST /auth/signup and POST /auth/login
    AuthResponse  → Output returned on successful signup/login
    ErrorResponse → Standard error shape (used by FastAPI's HTTPException)
"""

from pydantic import BaseModel, EmailStr


class AuthRequest(BaseModel):
    """
    Request body for signup and login.

    Fields:
        email    (EmailStr): User's email address. Pydantic validates the format
                             automatically (e.g. rejects "not-an-email").
        password (str):      User's password. Supabase enforces minimum strength.

    Example JSON:
        { "email": "user@example.com", "password": "MySecure123!" }
    """
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """
    Response returned after successful signup or login.

    Fields:
        access_token (str): Supabase JWT token. The frontend stores this and
                           sends it as "Authorization: Bearer <token>" on every request.
        user_id      (str): UUID of the authenticated user (from Supabase auth.users).
        email        (str): The user's email address.

    Example JSON:
        {
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "user_id": "a1b2c3d4-...",
            "email": "user@example.com"
        }
    """
    access_token: str
    user_id: str
    email: str


class ErrorResponse(BaseModel):
    """
    Standard error response shape.

    Fields:
        detail (str): Human-readable error message.

    Example JSON:
        { "detail": "Invalid credentials" }
    """
    detail: str
