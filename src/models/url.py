"""URL model for the frontier."""

import enum
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base


class URLStatus(enum.Enum):
    """URL crawling status."""

    PENDING = "pending"
    CRAWLING = "crawling"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class URL(Base):
    """
    URL model for the frontier.

    Represents a URL to be crawled or already crawled.
    Follows Single Responsibility Principle - only manages URL state.
    """

    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    domain = Column(String(255), index=True)
    status = Column(
        Enum(URLStatus),
        default=URLStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority = Column(Integer, default=0, nullable=False, index=True)
    crawl_attempts = Column(Integer, default=0, nullable=False)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationship to CrawledPage
    crawled_page = relationship("CrawledPage", back_populates="url", uselist=False)

    def __init__(self, **kwargs):  # type: ignore
        """Initialize URL and extract domain."""
        super().__init__(**kwargs)
        if self.url:
            self.domain = self._extract_domain(self.url)

    @staticmethod
    def _extract_domain(url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: Full URL

        Returns:
            Domain name

        Example:
            >>> URL._extract_domain("https://example.com/path")
            'example.com'
        """
        parsed = urlparse(url)
        return parsed.netloc

    def __repr__(self) -> str:
        """String representation of URL."""
        return f"<URL(id={self.id}, url='{self.url}', status={self.status.value})>"
