"""FastAPI application for Coordinator."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api import content, tasks, urls
from src.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Lookuply Coordinator",
    description="URL Frontier & Task Queue for Decentralized Crawler Network",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to log request bodies for debugging 422 errors
@app.middleware("http")
async def log_validation_errors(request: Request, call_next):
    """Log request bodies that might cause validation errors."""
    if request.url.path.endswith("/content") and request.method == "POST":
        # Read and restore body
        body = await request.body()

        # Call the endpoint
        response = await call_next(request)

        # Log if 422
        if response.status_code == 422:
            import json
            try:
                data = json.loads(body)
                logger.error(f"422 Validation Error on {request.url.path}")
                logger.error(f"  Title length: {len(str(data.get('title', '')))} chars")
                logger.error(f"  Content length: {len(str(data.get('content', '')))} chars")
                logger.error(f"  Language: {data.get('language')}")
                logger.error(f"  Author: {data.get('author')}")
                logger.error(f"  Date: {data.get('date')}")
                if len(str(data.get('content', ''))) < 100:
                    logger.error(f"  Content preview: {data.get('content')}")
            except Exception as e:
                logger.error(f"  Could not parse request body: {e}")
                logger.error(f"  Raw body (first 500 chars): {body[:500]}")

        return response
    else:
        return await call_next(request)


# Include routers
app.include_router(urls.router, prefix="/api/v1", tags=["urls"])
app.include_router(content.router, prefix="/api/v1/content", tags=["content"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Health status
    """
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.

    Returns:
        API information
    """
    return {
        "name": "Lookuply Coordinator",
        "version": "0.1.0",
        "docs": "/docs",
    }
