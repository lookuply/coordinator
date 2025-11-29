"""Tests for URL Frontier Service."""

import pytest
from sqlalchemy.orm import Session

from src.models.url import URL, URLStatus
from src.schemas.url import URLCreate
from src.services.frontier import FrontierService


class TestFrontierService:
    """Test URL Frontier Service."""

    def test_add_url(self, db_session: Session) -> None:
        """Test adding a URL to the frontier."""
        service = FrontierService(db_session)
        url_data = URLCreate(url="https://example.com", priority=5)

        url = service.add_url(url_data)

        assert url.id is not None
        assert url.url == "https://example.com"
        assert url.priority == 5
        assert url.status == URLStatus.PENDING
        assert url.domain == "example.com"

    def test_add_duplicate_url_returns_existing(self, db_session: Session) -> None:
        """Test adding a duplicate URL returns the existing one."""
        service = FrontierService(db_session)
        url_data = URLCreate(url="https://example.com")

        url1 = service.add_url(url_data)
        url2 = service.add_url(url_data)

        assert url1.id == url2.id

    def test_get_next_urls(self, db_session: Session, sample_urls: list[str]) -> None:
        """Test getting next URLs to crawl."""
        service = FrontierService(db_session)

        # Add URLs with different priorities
        for i, url in enumerate(sample_urls):
            service.add_url(URLCreate(url=url, priority=i))

        # Get top 3 URLs (should be highest priority)
        urls = service.get_next_urls(limit=3)

        assert len(urls) == 3
        # Should be ordered by priority descending
        assert urls[0].priority >= urls[1].priority >= urls[2].priority

    def test_get_next_urls_skips_non_pending(self, db_session: Session) -> None:
        """Test that get_next_urls only returns PENDING URLs."""
        service = FrontierService(db_session)

        # Add URLs with different statuses
        url1 = service.add_url(URLCreate(url="https://example.com/1"))
        url2 = service.add_url(URLCreate(url="https://example.com/2"))
        url3 = service.add_url(URLCreate(url="https://example.com/3"))

        # Mark url2 as crawling, url3 as completed
        service.mark_as_crawling(url2.id)
        service.mark_as_completed(url3.id)

        # Should only return url1
        urls = service.get_next_urls(limit=10)

        assert len(urls) == 1
        assert urls[0].id == url1.id

    def test_mark_as_crawling(self, db_session: Session) -> None:
        """Test marking URL as crawling."""
        service = FrontierService(db_session)
        url = service.add_url(URLCreate(url="https://example.com"))

        updated_url = service.mark_as_crawling(url.id)

        assert updated_url.status == URLStatus.CRAWLING

    def test_mark_as_completed(self, db_session: Session) -> None:
        """Test marking URL as completed."""
        service = FrontierService(db_session)
        url = service.add_url(URLCreate(url="https://example.com"))

        updated_url = service.mark_as_completed(url.id)

        assert updated_url.status == URLStatus.COMPLETED
        assert updated_url.last_crawled_at is not None

    def test_mark_as_failed(self, db_session: Session) -> None:
        """Test marking URL as failed."""
        service = FrontierService(db_session)
        url = service.add_url(URLCreate(url="https://example.com"))

        updated_url = service.mark_as_failed(url.id, "Connection timeout")

        assert updated_url.status == URLStatus.FAILED
        assert updated_url.error_message == "Connection timeout"
        assert updated_url.crawl_attempts == 1

    def test_get_url_count_by_status(self, db_session: Session) -> None:
        """Test getting URL count by status."""
        service = FrontierService(db_session)

        # Add URLs with different statuses
        url1 = service.add_url(URLCreate(url="https://example.com/1"))
        url2 = service.add_url(URLCreate(url="https://example.com/2"))
        url3 = service.add_url(URLCreate(url="https://example.com/3"))

        service.mark_as_crawling(url2.id)
        service.mark_as_completed(url3.id)

        counts = service.get_url_count_by_status()

        assert counts[URLStatus.PENDING] == 1
        assert counts[URLStatus.CRAWLING] == 1
        assert counts[URLStatus.COMPLETED] == 1
        assert counts.get(URLStatus.FAILED, 0) == 0

    def test_get_url_by_id(self, db_session: Session) -> None:
        """Test getting URL by ID."""
        service = FrontierService(db_session)
        url = service.add_url(URLCreate(url="https://example.com"))

        retrieved_url = service.get_url_by_id(url.id)

        assert retrieved_url is not None
        assert retrieved_url.id == url.id
        assert retrieved_url.url == url.url

    def test_get_url_by_id_not_found(self, db_session: Session) -> None:
        """Test getting non-existent URL returns None."""
        service = FrontierService(db_session)

        url = service.get_url_by_id(99999)

        assert url is None

    def test_delete_url(self, db_session: Session) -> None:
        """Test deleting a URL."""
        service = FrontierService(db_session)
        url = service.add_url(URLCreate(url="https://example.com"))

        result = service.delete_url(url.id)

        assert result is True
        assert service.get_url_by_id(url.id) is None

    def test_delete_url_not_found(self, db_session: Session) -> None:
        """Test deleting non-existent URL returns False."""
        service = FrontierService(db_session)

        result = service.delete_url(99999)

        assert result is False
