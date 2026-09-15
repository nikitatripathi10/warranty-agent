"""
Alembic environment script for Warranty Radar.

Reads DATABASE_URL from the environment (via .env) and imports the SQLAlchemy
metadata from app.models so that `alembic revision --autogenerate` detects
model changes automatically.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Make sure the backend/ directory is on the path so we can import app.*
_backend_dir = Path(__file__).resolve().parents[2]  # backend/
sys.path.insert(0, str(_backend_dir))

# Load .env before anything reads env vars
load_dotenv(_backend_dir / ".env")

from app.database import Base  # noqa: E402
import app.models  # noqa: E402 — ensure all models are registered against Base

# Alembic Config object
config = context.config

# Inject DATABASE_URL from environment (overrides any value in alembic.ini)
_db_url = os.getenv("DATABASE_URL")
if not _db_url:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy backend/.env.example to backend/.env "
        "and fill in your Postgres credentials."
    )
config.set_main_option("sqlalchemy.url", _db_url)

# Set up Python logging from the ini file section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (produces SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
