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
    """Create DB tables on startup (Alembic handles migrations; this is a safety net)."""
    logger.info("Warranty Radar backend starting up")
    # Tables are managed by Alembic migrations; Base.metadata.create_all is NOT
    # called here to avoid bypassing migration history.
    yield
    logger.info("Warranty Radar backend shutting down")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Warranty Radar API",
    description="Tracks purchases from Gmail and uploaded documents, extracts warranty data.",
    version="0.2.0",  # Milestone 2
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

_frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
_extra_origins = os.getenv("EXTRA_FRONTEND_ORIGINS", "")

_allowed_origins = [_frontend_origin]
if _extra_origins:
    _allowed_origins += [o.strip() for o in _extra_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router, tags=["Health"])
app.include_router(auth_gmail.router, prefix="/auth/gmail", tags=["Auth — Gmail OAuth"])
app.include_router(ingestion.router, prefix="/ingestion", tags=["Ingestion"])
app.include_router(extraction.router, prefix="/extraction", tags=["Extraction"])
