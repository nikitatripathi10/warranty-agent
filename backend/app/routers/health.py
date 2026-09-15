"""
GET /health — liveness probe.

Returns HTTP 200 with a JSON body so that load balancers, CI pipelines,
and the frontend can confirm the backend is reachable.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health_check() -> dict:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "warranty-radar-api",
        "milestone": 2,
    }
