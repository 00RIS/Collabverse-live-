"""
app/db/session.py

WHAT THIS FILE IS:
Creates the SQLAlchemy `engine` (the object that actually knows how to
talk to PostgreSQL over a connection pool) and `SessionLocal`, a factory
for creating individual database sessions.

WHY IT EXISTS:
A "session" is SQLAlchemy's unit-of-work object — it tracks the objects
you load/create/modify and turns them into SQL statements, wrapped in a
transaction, when you commit. We don't want one global session shared by
every request (concurrent requests would corrupt each other's state), so
instead we create a *fresh* session per request and close it when the
request ends. `get_db()` below is a FastAPI dependency that does exactly
that — FastAPI calls it before your endpoint runs, hands the session to
your endpoint, and guarantees it's closed afterward even if an error
occurs.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
