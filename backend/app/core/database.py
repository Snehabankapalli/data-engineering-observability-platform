"""Database engine and session factory.

Uses SQLAlchemy 2.0 synchronous API backed by psycopg2.
The async layer (if needed in future) can be layered on top by swapping
``create_engine`` for ``create_async_engine`` and adjusting the session type.

The module intentionally keeps this surface small.  All business logic
lives in service or route layers, never here.
"""

from __future__ import annotations

import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = structlog.get_logger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # detect stale connections before use
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,     # log SQL only in debug mode
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # avoid implicit lazy-loads after commit
)


def get_db():
    """FastAPI dependency that yields a database session.

    Opens a session at the start of each request and guarantees it is
    closed (and any pending transaction rolled back) when the request
    completes, even if an exception is raised.

    Yields:
        Session: An active SQLAlchemy session bound to the request scope.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables defined in the ORM metadata if they do not exist.

    This is called once at application startup.  For production migrations
    use Alembic (``alembic upgrade head``) rather than this function.

    Raises:
        sqlalchemy.exc.OperationalError: If the database is unreachable.
    """
    # Import models so that Base.metadata is populated before create_all.
    from app.models import pipeline  # noqa: F401
    from app.models.pipeline import Base

    Base.metadata.create_all(bind=engine)
    logger.info("database.tables_created")


def check_connection() -> bool:
    """Verify database connectivity with a lightweight probe query.

    Returns:
        True if the database responds, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("database.connection_check_failed", error=str(exc))
        return False
