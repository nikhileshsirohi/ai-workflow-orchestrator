from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Local dev DB (single file). Later we can switch to Postgres with one config change.
DATABASE_URL = "sqlite:///./ai_orchestrator.db"

# SQLite needs this flag when used from different threads (FastAPI can be multi-threaded).
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


def get_db_session():
    """
    Simple session generator.
    Usage:
        db = next(get_db_session())
        ...
        db.close()
    In FastAPI, we'll use dependency injection later.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()