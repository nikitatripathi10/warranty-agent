"""
Database engine, session factory, and declarative base.

All connection parameters come from the DATABASE_URL environment variable.
We never hardcode credentials here.
"""

import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

logger = logging.getLogger(__name__)

_database_url = os.getenv("DATABASE_URL")
if not _database_url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Copy backend/.env.example to backend/.env and fill in your credentials."
    )

# pool_pre_ping=True ensures stale connections from a hosted pool (Supabase/Neon)
# are detected and recycled automatically.
engine = create_engine(
    _database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,  # Set True temporarily to see raw SQL during debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base — imported by models.py and alembic env.py."""
    pass


def get_db():
    """
    FastAPI dependency that yields a database session and guarantees cleanup.

    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
