"""URL Frontier Service.

Manages the URL frontier - the queue of URLs to be crawled.
Follows SOLID principles:
- Single Responsibility: Only manages URL frontier
- Dependency Inversion: Depends on Session abstraction
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.url import URL, URLStatus
from src.schemas.url import URLCreate


class FrontierService:
    """
    URL Frontier Service.

    Manages the queue of URLs to be crawled.
    Provides methods for adding, retrieving, and updating URL statuses.
    """

    def __init__(self, db: Session):
        """
        Initialize frontier service.

        Args:
            db: Database session
        """
        self.db = db

    def add_url(self, url_data: URLCreate) -> URL:
        """
        Add URL to the frontier.

        If URL already exists, return the existing one.

        Args:
            url_data: URL data

        Returns:
            URL object

        Example:
            >>> service = FrontierService(db)
            >>> url = service.add_url(URLCreate(url="https://example.com"))
        """
        # Check if URL already exists
        existing_url = self.db.query(URL).filter(URL.url == url_data.url).first()
        if existing_url:
            return existing_url

        # Create new URL
        url = URL(
            url=url_data.url,
            priority=url_data.priority,
        )

        self.db.add(url)
        try:
            self.db.commit()
            self.db.refresh(url)
        except IntegrityError:
            # Handle race condition - URL was added by another process
            self.db.rollback()
            existing_url = self.db.query(URL).filter(URL.url == url_data.url).first()
            if existing_url:
                return existing_url
            raise

        return url

    def get_next_urls(self, limit: int = 10) -> list[URL]:
        """
        Get next URLs to crawl.

        Returns URLs with PENDING status, ordered by priority (highest first).

        Args:
            limit: Maximum number of URLs to return

        Returns:
            List of URLs to crawl

        Example:
            >>> service = FrontierService(db)
            >>> urls = service.get_next_urls(limit=5)
        """
        urls = (
            self.db.query(URL)
            .filter(URL.status == URLStatus.PENDING)
            .order_by(URL.priority.desc(), URL.created_at.asc())
            .limit(limit)
            .all()
        )
        return urls

    def mark_as_crawling(self, url_id: int) -> URL:
        """
        Mark URL as currently being crawled.

        Args:
            url_id: URL ID

        Returns:
            Updated URL

        Raises:
            ValueError: If URL not found
        """
        url = self.db.query(URL).filter(URL.id == url_id).first()
        if not url:
            raise ValueError(f"URL {url_id} not found")

        url.status = URLStatus.CRAWLING
        self.db.commit()
        self.db.refresh(url)
        return url

    def mark_as_completed(self, url_id: int) -> URL:
        """
        Mark URL as successfully crawled.

        Args:
            url_id: URL ID

        Returns:
            Updated URL

        Raises:
            ValueError: If URL not found
        """
        url = self.db.query(URL).filter(URL.id == url_id).first()
        if not url:
            raise ValueError(f"URL {url_id} not found")

        url.status = URLStatus.COMPLETED
        url.last_crawled_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(url)
        return url

    def mark_as_failed(self, url_id: int, error_message: str) -> URL:
        """
        Mark URL as failed to crawl.

        Args:
            url_id: URL ID
            error_message: Error description

        Returns:
            Updated URL

        Raises:
            ValueError: If URL not found
        """
        url = self.db.query(URL).filter(URL.id == url_id).first()
        if not url:
            raise ValueError(f"URL {url_id} not found")

        url.status = URLStatus.FAILED
        url.error_message = error_message
        url.crawl_attempts += 1
        self.db.commit()
        self.db.refresh(url)
        return url

    def get_url_count_by_status(self) -> dict[URLStatus, int]:
        """
        Get count of URLs grouped by status.

        Returns:
            Dictionary mapping status to count

        Example:
            >>> service = FrontierService(db)
            >>> counts = service.get_url_count_by_status()
            >>> print(counts[URLStatus.PENDING])
            42
        """
        results = (
            self.db.query(URL.status, func.count(URL.id))
            .group_by(URL.status)
            .all()
        )

        counts = {status: count for status, count in results}
        return counts

    def get_url_by_id(self, url_id: int) -> Optional[URL]:
        """
        Get URL by ID.

        Args:
            url_id: URL ID

        Returns:
            URL or None if not found
        """
        return self.db.query(URL).filter(URL.id == url_id).first()

    def delete_url(self, url_id: int) -> bool:
        """
        Delete URL from frontier.

        Args:
            url_id: URL ID

        Returns:
            True if deleted, False if not found
        """
        url = self.db.query(URL).filter(URL.id == url_id).first()
        if not url:
            return False

        self.db.delete(url)
        self.db.commit()
        return True
