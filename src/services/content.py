"""Content Management Service.

Manages crawled page content storage and indexing.
Follows SOLID principles:
- Single Responsibility: Only manages page content
- Dependency Inversion: Depends on Session abstraction
"""

from datetime import date as date_type, datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.models.crawled_page import CrawledPage
from src.models.url import URL, URLStatus


class ContentService:
    """
    Content Management Service.

    Manages storage and retrieval of crawled page content.
    Provides methods for storing content and tracking indexing status.
    """

    def __init__(self, db: Session):
        """
        Initialize content service.

        Args:
            db: Database session
        """
        self.db = db

    def store_content(
        self,
        url_id: int,
        title: Optional[str],
        content: str,
        language: Optional[str],
        author: Optional[str] = None,
        date: Optional[str] = None,
    ) -> CrawledPage:
        """
        Store crawled page content.

        Args:
            url_id: URL ID from urls table
            title: Page title
            content: Main text content
            language: Language code
            author: Author name
            date: Publication date

        Returns:
            Created or updated CrawledPage

        Raises:
            ValueError: If URL not found or not completed

        Example:
            >>> service = ContentService(db)
            >>> page = service.store_content(
            ...     url_id=1,
            ...     title="Example Page",
            ...     content="This is the content...",
            ...     language="en"
            ... )
        """
        # Validate URL exists and is completed
        url = self.db.query(URL).filter(URL.id == url_id).first()
        if not url:
            raise ValueError(f"URL {url_id} not found")

        if url.status not in [URLStatus.COMPLETED, URLStatus.CRAWLING]:
            raise ValueError(f"URL {url_id} has status {url.status.value}, expected COMPLETED or CRAWLING")

        # Parse date string to datetime if provided
        parsed_date: Optional[datetime] = None
        if date:
            try:
                # Try parsing as full datetime first
                parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # Try parsing as date-only (YYYY-MM-DD)
                try:
                    date_obj = date_type.fromisoformat(date)
                    parsed_date = datetime.combine(date_obj, datetime.min.time())
                except (ValueError, AttributeError):
                    # If parsing fails, leave as None
                    parsed_date = None

        # Check if content already exists
        existing = self.db.query(CrawledPage).filter(CrawledPage.url_id == url_id).first()
        if existing:
            # Update existing
            existing.title = title
            existing.content = content
            existing.language = language
            existing.author = author
            existing.date = parsed_date
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new
        page = CrawledPage(
            url_id=url_id,
            title=title,
            content=content,
            language=language,
            author=author,
            date=parsed_date,
        )
        self.db.add(page)
        self.db.commit()
        self.db.refresh(page)

        return page

    def mark_indexed(self, page_id: int) -> CrawledPage:
        """
        Mark page as indexed to Meilisearch.

        Args:
            page_id: CrawledPage ID

        Returns:
            Updated CrawledPage

        Raises:
            ValueError: If page not found

        Example:
            >>> service = ContentService(db)
            >>> page = service.mark_indexed(1)
        """
        page = self.db.query(CrawledPage).filter(CrawledPage.id == page_id).first()
        if not page:
            raise ValueError(f"Page {page_id} not found")

        page.indexed = True
        page.indexed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(page)

        return page

    def get_unindexed_pages(self, limit: int = 100) -> list[CrawledPage]:
        """
        Get pages that haven't been indexed yet.

        Args:
            limit: Maximum number of pages to return

        Returns:
            List of unindexed CrawledPage objects

        Example:
            >>> service = ContentService(db)
            >>> pages = service.get_unindexed_pages(limit=50)
        """
        return (
            self.db.query(CrawledPage)
            .filter(CrawledPage.indexed == False)
            .limit(limit)
            .all()
        )
