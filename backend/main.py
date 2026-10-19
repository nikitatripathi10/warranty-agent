"""
Warranty Radar — FastAPI application entry point.

Configures middleware, mounts all routers, and sets up structured logging
at startup. All configuration is read from environment variables via .env.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env before anything that reads env vars
load_dotenv()

from app.database import engine, Base  # noqa: E402 — after load_dotenv
from app.routers import health, auth_gmail, ingestion, extraction  # noqa: E402
from app.routers import purchases, alerts, agent  # noqa: E402

# ── Logging setup ─────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    """Start background scheduler on startup; shut it down cleanly on exit."""
    logger.info("Warranty Radar backend starting up (v0.5.0 — Milestone 5 Deployment)")

    # Tables are managed by Alembic migrations; Base.metadata.create_all is NOT
    # called here to avoid bypassing migration history.

    # Start the daily alert scheduler
    from app.services.alert_engine import start_scheduler
    start_scheduler()

    yield

    logger.info("Warranty Radar backend shutting down")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Warranty Radar API",
    description=(
        "Tracks purchases from Gmail and uploaded documents, extracts warranty data, "
        "schedules alerts, and answers natural-language queries about your purchases."
    ),
    version="0.5.0",  # Milestone 5 — Deployment
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

_frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
_extra_origins = os.getenv("EXTRA_FRONTEND_ORIGINS", "")

_allowed_origins = [o.rstrip("/") for o in [_frontend_origin] if o]
if _extra_origins:
    _allowed_origins.extend(
        o.strip().rstrip("/") for o in _extra_origins.split(",") if o.strip()
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router,        prefix="/health",      tags=["Health"])
app.include_router(auth_gmail.router,    prefix="/auth/gmail",  tags=["Auth"])
app.include_router(ingestion.router,     prefix="/ingestion",   tags=["Ingestion"])
app.include_router(extraction.router,    prefix="/extraction",  tags=["Extraction"])
app.include_router(purchases.router,     prefix="/purchases",   tags=["Purchases"])
app.include_router(alerts.router,        prefix="/alerts",      tags=["Alerts"])
app.include_router(agent.router,         prefix="/agent",       tags=["Agent"])
