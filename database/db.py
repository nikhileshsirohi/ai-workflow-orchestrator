from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.engine import Engine

from app.config import DATABASE_URL

# Create engine using the configured URL.
# For SQLite we keep check_same_thread=False and set PRAGMA below.
# For Postgres the connect_args are ignored.
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    future=True,
)

# For SQLite tune PRAGMA for better concurrency (WAL + busy timeout).
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    # Only run these pragmas for sqlite connections
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")  # 30s
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


def get_db_session():
    """
    Simple generator for DB sessions.
    Usage:
        db = next(get_db_session())
        ...
        db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()