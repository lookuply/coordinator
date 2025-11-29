"""Crawling tasks."""

from datetime import datetime, timedelta, timezone

from celery import Task
from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.database import SessionLocal
from src.models.url import URL, URLStatus
from src.services.frontier import FrontierService


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


@celery_app.task(base=DatabaseTask, bind=True, name="src.tasks.crawl.distribute_urls")
def distribute_urls(self: DatabaseTask, limit: int = 100) -> dict[str, int]:
    """
    Distribute pending URLs to crawler nodes.

    This task would be called by crawler nodes to get URLs to crawl.
    In production, this would communicate with actual crawler instances.

    Args:
        limit: Maximum number of URLs to distribute

    Returns:
        Statistics about distributed URLs
    """
    service = FrontierService(self.db)

    # Get pending URLs
    urls = service.get_next_urls(limit=limit)

    # Mark them as crawling (in production, assign to specific nodes)
    distributed = 0
    for url in urls:
        try:
            service.mark_as_crawling(url.id)
            distributed += 1
        except ValueError:
            # URL not found or already being crawled
            continue

    return {
        "distributed": distributed,
        "total_pending": len(urls),
    }


@celery_app.task(base=DatabaseTask, bind=True, name="src.tasks.crawl.cleanup_stale_crawling_urls")
def cleanup_stale_crawling_urls(self: DatabaseTask, timeout_minutes: int = 30) -> dict[str, int]:
    """
    Cleanup URLs that have been in CRAWLING state too long.

    If a crawler node crashes, URLs might get stuck in CRAWLING state.
    This task resets them to PENDING so they can be retried.

    Args:
        timeout_minutes: Minutes after which a CRAWLING URL is considered stale

    Returns:
        Statistics about cleaned up URLs
    """
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

    # Find stale crawling URLs
    stale_urls = (
        self.db.query(URL)
        .filter(
            URL.status == URLStatus.CRAWLING,
            URL.updated_at < cutoff_time,
        )
        .all()
    )

    # Reset them to PENDING
    cleaned = 0
    for url in stale_urls:
        url.status = URLStatus.PENDING
        url.crawl_attempts += 1
        cleaned += 1

    self.db.commit()

    return {
        "cleaned": cleaned,
        "cutoff_time": cutoff_time.isoformat(),
    }


@celery_app.task(base=DatabaseTask, bind=True, name="src.tasks.crawl.retry_failed_urls")
def retry_failed_urls(self: DatabaseTask, max_attempts: int = 3, limit: int = 100) -> dict[str, int]:
    """
    Retry failed URLs that haven't exceeded max attempts.

    Args:
        max_attempts: Maximum retry attempts before giving up
        limit: Maximum number of URLs to retry

    Returns:
        Statistics about retried URLs
    """
    # Find failed URLs with attempts < max_attempts
    failed_urls = (
        self.db.query(URL)
        .filter(
            URL.status == URLStatus.FAILED,
            URL.crawl_attempts < max_attempts,
        )
        .limit(limit)
        .all()
    )

    # Reset them to PENDING
    retried = 0
    for url in failed_urls:
        url.status = URLStatus.PENDING
        url.error_message = None
        retried += 1

    self.db.commit()

    return {
        "retried": retried,
        "max_attempts": max_attempts,
    }


@celery_app.task(base=DatabaseTask, bind=True, name="src.tasks.crawl.get_frontier_stats")
def get_frontier_stats(self: DatabaseTask) -> dict[str, int]:
    """
    Get statistics about the URL frontier.

    Returns:
        Statistics dictionary
    """
    service = FrontierService(self.db)
    counts = service.get_url_count_by_status()

    stats = {
        "pending": counts.get(URLStatus.PENDING, 0),
        "crawling": counts.get(URLStatus.CRAWLING, 0),
        "completed": counts.get(URLStatus.COMPLETED, 0),
        "failed": counts.get(URLStatus.FAILED, 0),
        "skipped": counts.get(URLStatus.SKIPPED, 0),
    }
    stats["total"] = sum(stats.values())

    return stats
