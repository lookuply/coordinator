"""Pytest configuration and fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database import Base


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Create a test database session.

    Uses SQLite in-memory database for fast tests.
    Each test gets a fresh database.
    """
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def sample_urls() -> list[str]:
    """Sample URLs for testing."""
    return [
        "https://example.com",
        "https://example.com/page1",
        "https://example.com/page2",
        "https://test.com",
        "https://test.com/about",
    ]
