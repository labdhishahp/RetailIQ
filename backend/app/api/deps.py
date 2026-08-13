from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database.session import get_db as _get_db

__all__ = ["get_db"]


def get_db() -> Generator[Session, None, None]:
    """Re-export database session dependency for API layer."""
    yield from _get_db()
