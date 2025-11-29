"""FastAPI application for Coordinator."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import urls
from src.config import settings

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

# Include routers
app.include_router(urls.router, prefix="/api/v1", tags=["urls"])


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
