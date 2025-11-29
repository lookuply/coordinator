"""Tests for URL model."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.url import URL, URLStatus


class TestURLModel:
    """Test URL model."""

    def test_create_url(self, db_session: Session) -> None:
        """Test creating a URL."""
        url = URL(url="https://example.com")

        db_session.add(url)
        db_session.commit()
        db_session.refresh(url)

        assert url.id is not None
        assert url.url == "https://example.com"
        assert url.status == URLStatus.PENDING
        assert url.priority == 0
        assert url.crawl_attempts == 0
        assert url.created_at is not None
        assert url.updated_at is not None

    def test_url_must_be_unique(self, db_session: Session) -> None:
        """Test that URL must be unique."""
        url1 = URL(url="https://example.com")
        url2 = URL(url="https://example.com")

        db_session.add(url1)
        db_session.commit()

        db_session.add(url2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_url_cannot_be_null(self, db_session: Session) -> None:
        """Test that URL cannot be null."""
        url = URL()

        db_session.add(url)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_url_status_enum(self, db_session: Session) -> None:
        """Test URL status transitions."""
        url = URL(url="https://example.com")
        db_session.add(url)
        db_session.commit()

        # Test all status transitions
        assert url.status == URLStatus.PENDING

        url.status = URLStatus.CRAWLING
        db_session.commit()
        assert url.status == URLStatus.CRAWLING

        url.status = URLStatus.COMPLETED
        db_session.commit()
        assert url.status == URLStatus.COMPLETED

    def test_url_priority(self, db_session: Session) -> None:
        """Test URL priority ordering."""
        url1 = URL(url="https://example.com/low", priority=1)
        url2 = URL(url="https://example.com/high", priority=10)
        url3 = URL(url="https://example.com/medium", priority=5)

        db_session.add_all([url1, url2, url3])
        db_session.commit()

        # Query by priority (highest first)
        urls = db_session.query(URL).order_by(URL.priority.desc()).all()

        assert urls[0].url == "https://example.com/high"
        assert urls[1].url == "https://example.com/medium"
        assert urls[2].url == "https://example.com/low"

    def test_url_timestamps(self, db_session: Session) -> None:
        """Test URL timestamps are set correctly."""
        url = URL(url="https://example.com")
        db_session.add(url)
        db_session.commit()
        db_session.refresh(url)

        assert url.created_at is not None
        assert url.updated_at is not None
        # Created and updated should be the same initially
        # (allowing small difference for processing time)
        assert abs((url.updated_at - url.created_at).total_seconds()) < 1

    def test_url_crawl_attempts_increment(self, db_session: Session) -> None:
        """Test crawl attempts can be incremented."""
        url = URL(url="https://example.com")
        db_session.add(url)
        db_session.commit()

        assert url.crawl_attempts == 0

        url.crawl_attempts += 1
        db_session.commit()
        assert url.crawl_attempts == 1

        url.crawl_attempts += 1
        db_session.commit()
        assert url.crawl_attempts == 2

    def test_url_domain_extraction(self, db_session: Session) -> None:
        """Test domain is extracted from URL."""
        url = URL(url="https://example.com/path/to/page?query=1")
        db_session.add(url)
        db_session.commit()

        assert url.domain == "example.com"

    def test_url_with_subdomain(self, db_session: Session) -> None:
        """Test domain extraction with subdomain."""
        url = URL(url="https://blog.example.com/post")
        db_session.add(url)
        db_session.commit()

        assert url.domain == "blog.example.com"

    def test_url_repr(self, db_session: Session) -> None:
        """Test URL string representation."""
        url = URL(url="https://example.com")
        db_session.add(url)
        db_session.commit()

        repr_str = repr(url)
        assert "URL" in repr_str
        assert "https://example.com" in repr_str
        assert str(url.id) in repr_str
