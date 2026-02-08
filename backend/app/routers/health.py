"""
health.py — Health Check Endpoint
==================================

Provides a simple GET /health endpoint that returns {"status": "ok"}.

Purpose:
    - Docker Compose health checks: ensures the backend container is alive.
    - Load balancers / monitoring: quick liveness probe.
    - Frontend: can ping this before attempting auth calls.

This endpoint is listed in PUBLIC_PATHS (middleware/auth.py) so it
does NOT require authentication — anyone can call it.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Service health check.

    Returns:
        dict: {"status": "ok"} if the server is running.

    Example:
        GET /health → 200 {"status": "ok"}
    """
    return {"status": "ok"}
