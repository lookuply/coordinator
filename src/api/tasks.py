"""Task API endpoints for AI evaluation workflow."""

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.crawled_page import CrawledPage
from src.models.url import URL
from src.schemas.task import (
    EvaluationResult,
    EvaluationResultResponse,
    PageResponse,
    PagesResponse,
    TaskResponse,
)

router = APIRouter()


def get_db_session(db: Session = Depends(get_db)) -> Session:
    """Get database session dependency."""
    return db


@router.get("/tasks/next", response_model=Optional[TaskResponse])
async def get_next_task(
    task_type: str = Query("evaluation", description="Task type"),
    db: Session = Depends(get_db_session),
) -> Optional[TaskResponse]:
    """
    Get next pending task for evaluation.

    Returns the oldest pending page that needs AI evaluation.
    Uses SELECT FOR UPDATE SKIP LOCKED for concurrent worker support.

    Args:
        task_type: Task type (currently only 'evaluation' supported)
        db: Database session

    Returns:
        Task data or None if no tasks available
    """
    if task_type != "evaluation":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported task type: {task_type}"
        )

    # Get oldest pending page with raw_html
    page = (
        db.query(CrawledPage)
        .join(URL, CrawledPage.url_id == URL.id)
        .filter(CrawledPage.evaluation_status == "pending")
        .filter(CrawledPage.content.isnot(None))  # Has content
        .order_by(CrawledPage.created_at.asc())
        .with_for_update(skip_locked=True)
        .first()
    )

    if not page:
        return None

    # Return task data
    # Note: We return 'content' as 'raw_html' for compatibility with ai-evaluator
    return TaskResponse(
        id=page.id,
        url=page.url.url,
        raw_html=page.content,  # Content is the extracted HTML
        depth=page.depth
    )


@router.post("/tasks/{task_id}/processing", response_model=EvaluationResultResponse)
async def mark_task_processing(
    task_id: int,
    db: Session = Depends(get_db_session),
) -> EvaluationResultResponse:
    """
    Mark task as being processed.

    Args:
        task_id: Page ID
        db: Database session

    Returns:
        Updated page

    Raises:
        HTTPException: If page not found
    """
    page = db.query(CrawledPage).filter(CrawledPage.id == task_id).first()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {task_id} not found"
        )

    # Update status
    page.evaluation_status = "processing"
    page.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(page)

    return EvaluationResultResponse(
        id=page.id,
        url_id=page.url_id,
        evaluation_status=page.evaluation_status,
        ai_score=page.ai_score,
        evaluated_at=page.evaluated_at
    )


@router.post("/tasks/{task_id}/result", response_model=EvaluationResultResponse)
async def submit_evaluation_result(
    task_id: int,
    result: EvaluationResult,
    db: Session = Depends(get_db_session),
) -> EvaluationResultResponse:
    """
    Submit evaluation result for a task.

    Args:
        task_id: Page ID
        result: Evaluation result data
        db: Database session

    Returns:
        Updated page

    Raises:
        HTTPException: If page not found
    """
    page = db.query(CrawledPage).filter(CrawledPage.id == task_id).first()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {task_id} not found"
        )

    # Update page with evaluation results
    page.title = result.title
    page.content = result.content
    page.summary = result.summary
    page.language = result.language
    page.ai_score = result.ai_score
    page.evaluation_status = "evaluated"
    page.evaluated_at = datetime.now(timezone.utc)
    page.evaluation_error = None
    page.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(page)

    return EvaluationResultResponse(
        id=page.id,
        url_id=page.url_id,
        evaluation_status=page.evaluation_status,
        ai_score=page.ai_score,
        evaluated_at=page.evaluated_at
    )


@router.post("/tasks/{task_id}/failed", response_model=EvaluationResultResponse)
async def mark_task_failed(
    task_id: int,
    error_data: dict[str, str],
    db: Session = Depends(get_db_session),
) -> EvaluationResultResponse:
    """
    Mark task as failed.

    Args:
        task_id: Page ID
        error_data: Error data with 'error' field
        db: Database session

    Returns:
        Updated page

    Raises:
        HTTPException: If page not found
    """
    page = db.query(CrawledPage).filter(CrawledPage.id == task_id).first()

    if not page:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page {task_id} not found"
        )

    # Update status to failed
    error_message = error_data.get("error", "Unknown error")
    page.evaluation_status = "failed"
    page.evaluation_error = error_message[:500]  # Limit error message length
    page.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(page)

    return EvaluationResultResponse(
        id=page.id,
        url_id=page.url_id,
        evaluation_status=page.evaluation_status,
        ai_score=page.ai_score,
        evaluated_at=page.evaluated_at
    )


@router.get("/pages", response_model=PagesResponse)
async def get_pages(
    status: str = Query("evaluated", description="Filter by evaluation status"),
    limit: int = Query(100, ge=1, le=1000, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db_session),
) -> PagesResponse:
    """
    Get pages with optional filtering.

    Used for syncing evaluated pages to Meilisearch.

    Args:
        status: Filter by evaluation status (pending, processing, evaluated, failed)
        limit: Maximum number of results
        offset: Pagination offset
        db: Database session

    Returns:
        List of pages with metadata
    """
    # Query pages with status filter
    query = (
        db.query(CrawledPage)
        .join(URL, CrawledPage.url_id == URL.id)
        .filter(CrawledPage.evaluation_status == status)
        .order_by(CrawledPage.evaluated_at.desc().nullslast())
    )

    # Get total count
    total_count = query.count()

    # Get paginated results
    pages = query.offset(offset).limit(limit).all()

    # Build response
    page_responses = [
        PageResponse(
            id=page.id,
            url=page.url.url,
            title=page.title,
            content=page.content,
            summary=page.summary,
            language=page.language,
            ai_score=page.ai_score,
            depth=page.depth,
            evaluation_status=page.evaluation_status,
            evaluated_at=page.evaluated_at,
            created_at=page.created_at
        )
        for page in pages
    ]

    return PagesResponse(
        pages=page_responses,
        count=total_count,
        offset=offset,
        limit=limit
    )


@router.get("/stats/evaluation")
async def get_evaluation_stats(
    db: Session = Depends(get_db_session),
) -> dict:
    """
    Get evaluation statistics.

    Returns:
        Statistics about page evaluation status
    """
    from sqlalchemy import func

    # Count by evaluation status
    status_counts = (
        db.query(
            CrawledPage.evaluation_status,
            func.count(CrawledPage.id).label("count")
        )
        .group_by(CrawledPage.evaluation_status)
        .all()
    )

    stats = {
        "pages_by_status": {status: count for status, count in status_counts},
        "total_pages": sum(count for _, count in status_counts)
    }

    # Count by depth
    depth_counts = (
        db.query(
            CrawledPage.depth,
            func.count(CrawledPage.id).label("count")
        )
        .group_by(CrawledPage.depth)
        .all()
    )

    stats["pages_by_depth"] = {f"depth_{depth}": count for depth, count in depth_counts}

    # Score distribution (for evaluated pages)
    score_ranges = [
        ("0-20", 0, 20),
        ("20-40", 20, 40),
        ("40-60", 40, 60),
        ("60-80", 60, 80),
        ("80-100", 80, 100),
    ]

    score_distribution = {}
    for label, min_score, max_score in score_ranges:
        count = (
            db.query(func.count(CrawledPage.id))
            .filter(CrawledPage.ai_score >= min_score)
            .filter(CrawledPage.ai_score < max_score)
            .scalar()
        )
        score_distribution[label] = count

    # Handle 100 exactly
    count_100 = (
        db.query(func.count(CrawledPage.id))
        .filter(CrawledPage.ai_score == 100)
        .scalar()
    )
    score_distribution["80-100"] += count_100

    stats["score_distribution"] = score_distribution

    # Language distribution
    lang_counts = (
        db.query(
            CrawledPage.language,
            func.count(CrawledPage.id).label("count")
        )
        .filter(CrawledPage.language.isnot(None))
        .group_by(CrawledPage.language)
        .order_by(func.count(CrawledPage.id).desc())
        .limit(10)
        .all()
    )

    stats["languages"] = {lang: count for lang, count in lang_counts}

    return stats
