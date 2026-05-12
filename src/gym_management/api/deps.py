"""FastAPI dependencies (database session per request)."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from gym_management.infrastructure.database import get_session_factory


def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
