"""Pydantic schemas for content submission."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContentSubmission(BaseModel):
    """Schema for submitting crawled page content."""

    title: Optional[str] = Field(None, max_length=500, description="Page title")
    content: str = Field(..., min_length=50, description="Main text content")
    language: Optional[str] = Field(None, max_length=10, description="Language code (e.g., 'en', 'sk')")
    author: Optional[str] = Field(None, max_length=255, description="Author name")
    date: Optional[datetime] = Field(None, description="Publication date")


class ContentResponse(BaseModel):
    """Response after content submission."""

    model_config = {"from_attributes": True}  # Enable ORM mode

    id: int
    url_id: int
    title: Optional[str]
    language: Optional[str]
    indexed: bool
    created_at: datetime
