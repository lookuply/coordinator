"""Content submission API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.content import ContentResponse, ContentSubmission
from src.services.content import ContentService

router = APIRouter()


def get_content_service(db: Session = Depends(get_db)) -> ContentService:
    """
    Get content service instance.

    Args:
        db: Database session

    Returns:
        ContentService instance
    """
    return ContentService(db)


@router.post("/urls/{url_id}/content", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def submit_content(
    url_id: int,
    submission: ContentSubmission,
    service: Annotated[ContentService, Depends(get_content_service)],
) -> ContentResponse:
    """
    Submit crawled page content.

    Called by crawler after extracting content from a page.
    Triggers async indexing task to Meilisearch.

    Args:
        url_id: URL ID
        submission: Content data
        service: Content service

    Returns:
        Created page content

    Raises:
        HTTPException: If URL not found or invalid status

    Example:
        >>> POST /api/v1/content/urls/123/content
        >>> {
        ...     "title": "Example Page",
        ...     "content": "This is the main content...",
        ...     "language": "en"
        ... }
    """
    try:
        page = service.store_content(
            url_id=url_id,
            title=submission.title,
            content=submission.content,
            language=submission.language,
            author=submission.author,
            date=submission.date,
        )

        # Trigger async indexing task
        # Import here to avoid circular dependency
        from src.tasks.index import index_to_meilisearch
        index_to_meilisearch.delay(page.id)

        return ContentResponse.model_validate(page)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
