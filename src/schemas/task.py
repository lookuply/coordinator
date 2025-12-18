"""Task schemas for AI evaluation workflow."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskResponse(BaseModel):
    """Task for AI evaluation."""

    id: int = Field(..., description="Page ID")
    url: str = Field(..., description="Page URL")
    raw_html: str = Field(..., description="Raw HTML content")
    depth: int = Field(default=0, description="Crawl depth")

    model_config = {"from_attributes": True}


class EvaluationResult(BaseModel):
    """Result from AI evaluation."""

    title: str = Field(..., max_length=200, description="Page title")
    content: str = Field(..., max_length=10000, description="Extracted main content")
    summary: str = Field(..., max_length=500, description="2-3 sentence summary")
    language: str = Field(..., max_length=10, description="Language code (ISO 639-1)")
    ai_score: int = Field(..., ge=0, le=100, description="Quality score 0-100")


class EvaluationResultResponse(BaseModel):
    """Response after submitting evaluation result."""

    id: int = Field(..., description="Page ID")
    url_id: int = Field(..., description="URL ID")
    evaluation_status: str = Field(..., description="Evaluation status")
    ai_score: Optional[int] = Field(None, description="AI quality score")
    evaluated_at: Optional[datetime] = Field(None, description="Evaluation timestamp")

    model_config = {"from_attributes": True}


class PageResponse(BaseModel):
    """Page with evaluation data."""

    id: int
    url: str
    title: Optional[str] = None
    content: str
    summary: Optional[str] = None
    language: Optional[str] = None
    ai_score: Optional[int] = None
    depth: int = 0
    evaluation_status: str
    evaluated_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PagesResponse(BaseModel):
    """Response with list of pages."""

    pages: list[PageResponse]
    count: int
    offset: int
    limit: int
