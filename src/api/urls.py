"""URL API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.url import URLStatus
from src.schemas.url import URLBatchCreate, URLBatchResponse, URLCreate, URLResponse
from src.services.frontier import FrontierService

router = APIRouter()


def get_frontier_service(db: Session = Depends(get_db)) -> FrontierService:
    """
    Get frontier service instance.

    Args:
        db: Database session

    Returns:
        FrontierService instance
    """
    return FrontierService(db)


@router.post("/urls", response_model=URLResponse)
async def add_url(
    url_data: URLCreate,
    service: Annotated[FrontierService, Depends(get_frontier_service)],
) -> tuple[URLResponse, int]:
    """
    Add URL to the frontier.

    If URL already exists, returns existing URL with 200 status.
    If new URL created, returns 201 status.

    Args:
        url_data: URL data
        service: Frontier service

    Returns:
        URL object and status code
    """
    from datetime import datetime, timezone
    from fastapi import Response
    from fastapi.responses import JSONResponse

    # Check if URL already exists
    from src.models.url import URL
    existing_url = service.db.query(URL).filter(URL.url == url_data.url).first()

    url = service.add_url(url_data)
    response_data = URLResponse.model_validate(url)

    # Return different status codes
    if existing_url:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data.model_dump(mode='json'),
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=response_data.model_dump(mode='json'),
        )


@router.get("/urls", response_model=list[URLResponse])
async def get_next_urls(
    service: Annotated[FrontierService, Depends(get_frontier_service)],
    limit: int = 10,
) -> list[URLResponse]:
    """
    Get next URLs to crawl.

    Returns URLs with PENDING status, ordered by priority.

    Args:
        limit: Maximum number of URLs to return
        service: Frontier service

    Returns:
        List of URLs
    """
    urls = service.get_next_urls(limit=limit)
    return [URLResponse.model_validate(url) for url in urls]


@router.get("/urls/{url_id}", response_model=URLResponse)
async def get_url(
    url_id: int,
    service: Annotated[FrontierService, Depends(get_frontier_service)],
) -> URLResponse:
    """
    Get URL by ID.

    Args:
        url_id: URL ID
        service: Frontier service

    Returns:
        URL object

    Raises:
        HTTPException: If URL not found
    """
    url = service.get_url_by_id(url_id)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"URL {url_id} not found",
        )
    return URLResponse.model_validate(url)


@router.delete("/urls/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    url_id: int,
    service: Annotated[FrontierService, Depends(get_frontier_service)],
) -> None:
    """
    Delete URL from frontier.

    Args:
        url_id: URL ID
        service: Frontier service

    Raises:
        HTTPException: If URL not found
    """
    success = service.delete_url(url_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"URL {url_id} not found",
        )


@router.post("/urls/{url_id}/crawling", response_model=URLResponse)
async def mark_as_crawling(
    url_id: int,
    service: Annotated[FrontierService, Depends(get_frontier_service)],
) -> URLResponse:
    """
    Mark URL as currently being crawled.

    Args:
        url_id: URL ID
        service: Frontier service

    Returns:
        Updated URL

    Raises:
        HTTPException: If URL not found
    """
    try:
        url = service.mark_as_crawling(url_id)
        return URLResponse.model_validate(url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/urls/{url_id}/completed", response_model=URLResponse)
async def mark_as_completed(
    url_id: int,
    service: Annotated[FrontierService, Depends(get_frontier_service)],
) -> URLResponse:
    """
    Mark URL as successfully crawled.

    Args:
        url_id: URL ID
        service: Frontier service

    Returns:
        Updated URL

    Raises:
        HTTPException: If URL not found
    """
    try:
        url = service.mark_as_completed(url_id)
        return URLResponse.model_validate(url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/urls/{url_id}/failed", response_model=URLResponse)
async def mark_as_failed(
    url_id: int,
    error_data: dict[str, str],
    service: Annotated[FrontierService, Depends(get_frontier_service)],
) -> URLResponse:
    """
    Mark URL as failed to crawl.

    Args:
        url_id: URL ID
        error_data: Error data with 'error_message' field
        service: Frontier service

    Returns:
        Updated URL

    Raises:
        HTTPException: If URL not found
    """
    try:
        error_message = error_data.get("error_message", "Unknown error")
        url = service.mark_as_failed(url_id, error_message)
        return URLResponse.model_validate(url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/urls/batch", response_model=URLBatchResponse)
async def add_urls_batch(
    batch_data: URLBatchCreate,
    service: Annotated[FrontierService, Depends(get_frontier_service)],
) -> URLBatchResponse:
    """
    Add multiple URLs to the frontier in batch.

    Efficiently adds multiple URLs at once. Skips URLs that already exist.
    Maximum 100 URLs per request.

    Args:
        batch_data: Batch of URLs to add
        service: Frontier service

    Returns:
        Batch operation result with counts
    """
    from src.models.url import URL

    added_urls = []
    skipped_count = 0

    for url_data in batch_data.urls:
        # Check if URL already exists
        existing_url = service.db.query(URL).filter(URL.url == url_data.url).first()

        if existing_url:
            skipped_count += 1
            continue

        # Add new URL
        try:
            url = service.add_url(url_data)
            added_urls.append(url.url)
        except Exception:
            # Skip URLs that fail validation or insertion
            skipped_count += 1
            continue

    return URLBatchResponse(
        added=len(added_urls),
        skipped=skipped_count,
        total=len(batch_data.urls),
        sample_added=added_urls[:5],  # Return first 5 as sample
    )


@router.get("/stats")
async def get_stats(
    service: Annotated[FrontierService, Depends(get_frontier_service)],
) -> dict[str, int]:
    """
    Get URL statistics.

    Returns count of URLs by status.

    Args:
        service: Frontier service

    Returns:
        Statistics dictionary
    """
    counts = service.get_url_count_by_status()

    # Convert to dict with string keys and ensure all statuses present
    stats = {
        "pending": counts.get(URLStatus.PENDING, 0),
        "crawling": counts.get(URLStatus.CRAWLING, 0),
        "completed": counts.get(URLStatus.COMPLETED, 0),
        "failed": counts.get(URLStatus.FAILED, 0),
        "skipped": counts.get(URLStatus.SKIPPED, 0),
    }

    # Add total
    stats["total"] = sum(stats.values())

    return stats
