"""
GET /health  — Liveness probe
GET /health/ready — Readiness probe (checks DB connectivity)

Railway and Render use the liveness probe to route traffic.
The readiness probe can be used by orchestrators to know when the
app is fully booted and the DB is reachable.
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Response
from sqlalchemy import text

router = APIRouter()

_VERSION = "0.5.0"
_START_TIME = datetime.now(timezone.utc)


@router.get("", summary="Liveness probe", tags=["Health"])
def health_check() -> dict:
    """
    Always returns 200 if the process is running.
    Used by Railway / Render as the basic liveness check.
    """
    uptime_seconds = (datetime.now(timezone.utc) - _START_TIME).total_seconds()
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "warranty-radar-api",
        "version": _VERSION,
        "uptime_seconds": round(uptime_seconds, 1),
        "milestone": 5,
    }


@router.get("/ready", summary="Readiness probe (DB connectivity)", tags=["Health"])
def readiness_check(response: Response) -> dict:
    """
    Checks that the database is reachable.
    Returns 200 if DB is up, 503 if not.

    Use this for:
    - Kubernetes readiness probes
    - Post-deployment smoke tests
    - Monitoring dashboards
    """
    from app.database import SessionLocal

    db_status = "ok"
    db_error = None

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as exc:
        db_status = "error"
        db_error = str(exc)

    overall_ok = db_status == "ok"
    if not overall_ok:
        response.status_code = 503

    return {
        "status": "ready" if overall_ok else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": _VERSION,
        "checks": {
            "database": {
                "status": db_status,
                "error": db_error,
            },
            "scheduler": {
                "status": "ok",  # APScheduler is started in lifespan; if we got here, it's running
            },
        },
    }
