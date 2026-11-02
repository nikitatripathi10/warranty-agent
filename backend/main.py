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

_default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://warranty-agent-nikita-54bd.vercel.app",
    "https://venerable-boba-fb4868.netlify.app",
    # Same-origin SPA served by this backend.
    "https://warranty-agent.onrender.com",
]

_frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
_extra_origins = os.getenv("EXTRA_FRONTEND_ORIGINS", "").strip()

_allowed_origins = list(_default_origins)
if _frontend_origin:
    _allowed_origins.append(_frontend_origin.rstrip("/"))
if _extra_origins:
    _allowed_origins.extend(
        o.strip().rstrip("/") for o in _extra_origins.split(",") if o.strip()
    )

app.add_middleware(
    CORSMiddleware,
    # Exact origins only. A wildcard *.vercel.app / *.netlify.app rule would let
    # anyone deploy a lookalike site and call the API with a stolen workspace token.
    allow_origins=list(set(_allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router,        prefix="/health",      tags=["Health"])
app.include_router(auth_gmail.signin_router, prefix="/auth/google", tags=["Auth"])
app.include_router(auth_gmail.router,    prefix="/auth/gmail",  tags=["Auth"])
app.include_router(ingestion.router,     prefix="/ingestion",   tags=["Ingestion"])
app.include_router(extraction.router,    prefix="/extraction",  tags=["Extraction"])
app.include_router(purchases.router,     prefix="/purchases",   tags=["Purchases"])
app.include_router(alerts.router,        prefix="/alerts",      tags=["Alerts"])
app.include_router(agent.router,         prefix="/agent",       tags=["Agent"])

# ── Optional: serve the built SPA from this same process ─────────────────────
# The Docker image copies frontend/dist here so one deploy covers API + UI.
# The mount is conditional, so deployments that only build the backend are
# unaffected. It is registered last so every API route above wins.
from pathlib import Path  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

_frontend_dist = os.getenv("FRONTEND_DIST", "").strip() or str(
    Path(__file__).resolve().parent / "frontend_dist"
)
if Path(_frontend_dist, "index.html").is_file():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
    logger.info("Serving frontend SPA from %s", _frontend_dist)
