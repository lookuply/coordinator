"""CrawledPage model for storing page content."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.database import Base


class CrawledPage(Base):
    """
    Crawled page content.

    Stores extracted content from successfully crawled pages.
    Indexed to Meilisearch via Celery task.
    Follows Single Responsibility Principle - only manages page content storage.
    """

    __tablename__ = "crawled_pages"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("urls.id", ondelete="CASCADE"), unique=True, nullable=False)
    title = Column(String(2000), nullable=True)
    content = Column(Text, nullable=False)
    language = Column(String(10), nullable=True)
    author = Column(String(255), nullable=True)
    date = Column(DateTime(timezone=True), nullable=True)
    indexed = Column(Boolean, default=False, nullable=False, index=True)
    indexed_at = Column(DateTime(timezone=True), nullable=True)
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

    # Relationship to URL
    url = relationship("URL", back_populates="crawled_page")

    def __repr__(self) -> str:
        """String representation of CrawledPage."""
        return f"<CrawledPage(id={self.id}, url_id={self.url_id}, title='{self.title}')>"
