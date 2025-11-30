"""Pydantic schemas for URL."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from src.models.url import URLStatus


class URLBase(BaseModel):
    """Base URL schema."""

    url: str = Field(..., max_length=2048, description="URL to crawl")
    priority: int = Field(default=0, ge=0, le=100, description="Priority (0-100, higher = more important)")


class URLCreate(URLBase):
    """Schema for creating a URL."""

    pass


class URLUpdate(BaseModel):
    """Schema for updating a URL."""

    status: Optional[URLStatus] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    error_message: Optional[str] = None


class URLResponse(URLBase):
    """Schema for URL response."""

    model_config = {"from_attributes": True}  # Enable ORM mode

    id: int
    domain: str
    status: URLStatus
    crawl_attempts: int
    last_crawled_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class URLBatchCreate(BaseModel):
    """Schema for batch creating URLs."""

    urls: list[URLCreate] = Field(..., min_length=1, max_length=100, description="List of URLs to add (max 100)")


class URLBatchResponse(BaseModel):
    """Schema for batch operation response."""

    added: int = Field(..., description="Number of URLs added")
    skipped: int = Field(..., description="Number of URLs skipped (already exist)")
    total: int = Field(..., description="Total URLs processed")
    sample_added: list[str] = Field(default_factory=list, description="Sample of added URLs (first 5)")
