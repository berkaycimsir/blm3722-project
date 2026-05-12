"""SQLite only — one file `gym.db` in your current working directory."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gym_management.infrastructure.orm_models import Base

# Start the app from the project root (`yazmuh`) so `gym.db` appears there.
_SQLITE_FILE = Path.cwd() / "gym.db"

_engine = None
_SessionLocal = None


def init_engine() -> None:
    """Create engine pointing at ./gym.db (SQLite)."""
    global _engine, _SessionLocal
    path = _SQLITE_FILE.resolve().as_posix()
    url = f"sqlite:///{path}"
    _engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def create_schema() -> None:
    if _engine is None:
        msg = "Call init_engine() first."
        raise RuntimeError(msg)
    Base.metadata.create_all(bind=_engine)


def get_session_factory():
    if _SessionLocal is None:
        msg = "Call init_engine() first."
        raise RuntimeError(msg)
    return _SessionLocal
