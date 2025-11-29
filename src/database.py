"""Database connection and session management."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import settings

# Create engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.log_level == "DEBUG",
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Base class for models
class Base(DeclarativeBase):
    """Base class for all models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.

    Yields:
        Database session

    Example:
        >>> from src.database import get_db
        >>> db = next(get_db())
        >>> # Use db
        >>> db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database (create all tables)."""
    Base.metadata.create_all(bind=engine)
