"""Celery application configuration."""

from celery import Celery

from src.config import settings

# Create Celery app
celery_app = Celery(
    "coordinator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.tasks.crawl", "src.tasks.index"],  # Import task modules
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,  # One task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
)

# Task routes disabled - all tasks go to default "celery" queue
# celery_app.conf.task_routes = {
#     "src.tasks.crawl.*": {"queue": "crawl"},
#     "src.tasks.index.*": {"queue": "index"},
# }

# Celery beat schedule (periodic tasks)
celery_app.conf.beat_schedule = {
    "cleanup-stale-urls": {
        "task": "src.tasks.crawl.cleanup_stale_crawling_urls",
        "schedule": 300.0,  # Every 5 minutes
    },
}
