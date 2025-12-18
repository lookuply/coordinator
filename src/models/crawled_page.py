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
    Includes AI evaluation workflow fields.
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

    # AI Evaluation fields
    ai_score = Column(Integer, nullable=True, index=True)  # 0-100 quality score
    summary = Column(Text, nullable=True)  # 2-3 sentence AI-generated summary
    evaluation_status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True
    )  # pending, processing, evaluated, failed
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    evaluation_error = Column(Text, nullable=True)  # Error message if evaluation failed

    # Crawl depth tracking
    depth = Column(Integer, default=0, nullable=False, index=True)
    parent_url_id = Column(Integer, ForeignKey("urls.id", ondelete="SET NULL"), nullable=True)

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

    # Relationships
    url = relationship("URL", back_populates="crawled_page", foreign_keys=[url_id])
    parent_url = relationship("URL", foreign_keys=[parent_url_id])

    def __repr__(self) -> str:
        """String representation of CrawledPage."""
        return f"<CrawledPage(id={self.id}, url_id={self.url_id}, title='{self.title}')>"
