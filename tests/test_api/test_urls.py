"""Tests for URL API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import app
from src.models.url import URLStatus

# Create test database with shared connection using StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Share one connection across all threads
)

# Create tables once
Base.metadata.create_all(bind=engine)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_database():
    """Clear all data from tables before each test."""
    db = TestingSessionLocal()
    try:
        # Delete all rows from tables
        from src.models.url import URL
        db.query(URL).delete()
        db.commit()
    finally:
        db.close()
    yield


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self):
        """Test health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestRootEndpoint:
    """Test root endpoint."""

    def test_root(self):
        """Test root returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Lookuply Coordinator"
        assert data["version"] == "0.1.0"


class TestURLEndpoints:
    """Test URL API endpoints."""

    def test_add_url(self):
        """Test adding a URL."""
        response = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com", "priority": 5},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["url"] == "https://example.com"
        assert data["priority"] == 5
        assert data["status"] == "pending"
        assert data["domain"] == "example.com"
        assert "id" in data

    def test_add_url_default_priority(self):
        """Test adding URL with default priority."""
        response = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["priority"] == 0

    def test_add_duplicate_url(self):
        """Test adding duplicate URL returns existing."""
        # Add first time
        response1 = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com"},
        )
        assert response1.status_code == 201

        # Add duplicate
        response2 = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com"},
        )
        assert response2.status_code == 200
        assert response1.json()["id"] == response2.json()["id"]

    def test_add_url_invalid_priority(self):
        """Test adding URL with invalid priority."""
        response = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com", "priority": 150},
        )

        assert response.status_code == 422  # Validation error

    def test_get_next_urls(self):
        """Test getting next URLs to crawl."""
        # Add some URLs
        for i in range(5):
            client.post(
                "/api/v1/urls",
                json={"url": f"https://example.com/page{i}", "priority": i},
            )

        # Get next URLs
        response = client.get("/api/v1/urls?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # Should be ordered by priority descending
        assert data[0]["priority"] >= data[1]["priority"] >= data[2]["priority"]

    def test_get_url_by_id(self):
        """Test getting URL by ID."""
        # Add URL
        response1 = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com"},
        )
        url_id = response1.json()["id"]

        # Get by ID
        response2 = client.get(f"/api/v1/urls/{url_id}")

        assert response2.status_code == 200
        data = response2.json()
        assert data["id"] == url_id
        assert data["url"] == "https://example.com"

    def test_get_url_by_id_not_found(self):
        """Test getting non-existent URL."""
        response = client.get("/api/v1/urls/99999")

        assert response.status_code == 404

    def test_delete_url(self):
        """Test deleting a URL."""
        # Add URL
        response1 = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com"},
        )
        url_id = response1.json()["id"]

        # Delete URL
        response2 = client.delete(f"/api/v1/urls/{url_id}")

        assert response2.status_code == 204

        # Verify deleted
        response3 = client.get(f"/api/v1/urls/{url_id}")
        assert response3.status_code == 404

    def test_delete_url_not_found(self):
        """Test deleting non-existent URL."""
        response = client.delete("/api/v1/urls/99999")

        assert response.status_code == 404

    def test_mark_url_as_crawling(self):
        """Test marking URL as crawling."""
        # Add URL
        response1 = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com"},
        )
        url_id = response1.json()["id"]

        # Mark as crawling
        response2 = client.post(f"/api/v1/urls/{url_id}/crawling")

        assert response2.status_code == 200
        data = response2.json()
        assert data["status"] == "crawling"

    def test_mark_url_as_completed(self):
        """Test marking URL as completed."""
        # Add URL
        response1 = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com"},
        )
        url_id = response1.json()["id"]

        # Mark as completed
        response2 = client.post(f"/api/v1/urls/{url_id}/completed")

        assert response2.status_code == 200
        data = response2.json()
        assert data["status"] == "completed"
        assert data["last_crawled_at"] is not None

    def test_mark_url_as_failed(self):
        """Test marking URL as failed."""
        # Add URL
        response1 = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com"},
        )
        url_id = response1.json()["id"]

        # Mark as failed
        response2 = client.post(
            f"/api/v1/urls/{url_id}/failed",
            json={"error_message": "Connection timeout"},
        )

        assert response2.status_code == 200
        data = response2.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Connection timeout"
        assert data["crawl_attempts"] == 1

    def test_get_stats(self):
        """Test getting URL statistics."""
        # Add URLs with different statuses
        url1_response = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com/1"},
        )
        url2_response = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com/2"},
        )
        url3_response = client.post(
            "/api/v1/urls",
            json={"url": "https://example.com/3"},
        )

        # Mark with different statuses
        client.post(f"/api/v1/urls/{url2_response.json()['id']}/crawling")
        client.post(f"/api/v1/urls/{url3_response.json()['id']}/completed")

        # Get stats
        response = client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 1
        assert data["crawling"] == 1
        assert data["completed"] == 1
        assert data["total"] == 3
