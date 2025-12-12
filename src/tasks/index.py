"""Indexing tasks for Meilisearch."""

import os
from datetime import datetime

import requests
from celery import Task
from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.crawled_page import CrawledPage


class DatabaseTask(Task):
    """Base task with database session."""

    _db: Session | None = None

    @property
    def db(self) -> Session:
        """Get database session."""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs) -> None:  # type: ignore
        """Close database session after task completes."""
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name="src.tasks.index.index_to_meilisearch",
    max_retries=3,
    default_retry_delay=60,  # 1 minute
)
def index_to_meilisearch(self: DatabaseTask, page_id: int) -> dict[str, any]:  # type: ignore
    """
    Index crawled page to Meilisearch.

    Args:
        page_id: CrawledPage ID

    Returns:
        Status dict with success info

    Raises:
        Exception: If indexing fails (will trigger retry)

    Example:
        >>> from src.tasks.index import index_to_meilisearch
        >>> result = index_to_meilisearch.delay(page_id=1)
    """
    # Fetch page from database
    page = self.db.query(CrawledPage).filter(CrawledPage.id == page_id).first()
    if not page:
        raise ValueError(f"Page {page_id} not found")

    # Get Meilisearch configuration
    meili_url = os.getenv("MEILISEARCH_URL", "http://meilisearch:7700")
    meili_key = os.getenv("MEILISEARCH_KEY")

    if not meili_key:
        raise ValueError("MEILISEARCH_KEY environment variable not set")

    # Format document for Meilisearch
    document = {
        "id": str(page.id),
        "url": page.url.url,
        "title": page.title or "Untitled",
        "content": page.content,
        "language": page.language or "unknown",
        "indexed_at": datetime.now().isoformat(),
    }

    # Index to Meilisearch
    try:
        response = requests.post(
            f"{meili_url}/indexes/pages/documents",
            headers={
                "Authorization": f"Bearer {meili_key}",
                "Content-Type": "application/json",
            },
            json=[document],
            timeout=10,
        )
        response.raise_for_status()

        # Mark as indexed
        page.indexed = True
        page.indexed_at = datetime.now()
        self.db.commit()

        return {
            "page_id": page_id,
            "url": page.url.url,
            "status": "indexed",
            "task_uid": response.json().get("taskUid"),
        }

    except requests.RequestException as e:
        # Retry on network errors
        raise self.retry(exc=e)


@celery_app.task(base=DatabaseTask, bind=True, name="src.tasks.index.batch_index_unindexed")
def batch_index_unindexed(self: DatabaseTask, limit: int = 100) -> dict[str, int]:
    """
    Batch index unindexed pages.

    Args:
        limit: Maximum number of pages to index

    Returns:
        Status dict with counts

    Example:
        >>> from src.tasks.index import batch_index_unindexed
        >>> result = batch_index_unindexed.delay(limit=50)
    """
    from src.services.content import ContentService

    service = ContentService(self.db)
    pages = service.get_unindexed_pages(limit=limit)

    # Trigger indexing for each page
    for page in pages:
        index_to_meilisearch.delay(page.id)

    return {
        "queued": len(pages),
        "limit": limit,
    }
