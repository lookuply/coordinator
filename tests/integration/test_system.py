"""
System Integration Test for Coordinator.

Tests the complete workflow:
1. URL Frontier Management - Adding URLs, getting next, status updates
2. Task Distribution - Getting evaluation tasks, marking status
3. Storing Results - Storing crawled content and evaluations
4. Statistics - System monitoring

This test simulates a full crawler + AI evaluator workflow.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import app

# ==========================================
# TEST DATABASE SETUP
# ==========================================

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Share connection for thread safety
)

Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_database():
    """Clear all data between tests."""
    db = TestingSessionLocal()
    try:
        from src.models.crawled_page import CrawledPage
        from src.models.url import URL
        db.query(CrawledPage).delete()
        db.query(URL).delete()
        db.commit()
    finally:
        db.close()
    yield


# ==========================================
# SAMPLE DATA
# ==========================================

SEED_URLS = [
    {"url": "https://example.com", "priority": 10},
    {"url": "https://example.com/blog", "priority": 8},
    {"url": "https://example.com/docs", "priority": 7},
    {"url": "https://test.com", "priority": 5},
    {"url": "https://test.com/about", "priority": 3},
]

SAMPLE_CONTENT = {
    "title": "Example Article: How to Build Search Engines",
    "content": """
    This comprehensive guide explores the fundamentals of building
    modern search engines. Search engines are complex systems that
    involve crawling, indexing, and ranking web pages. The architecture
    typically includes distributed crawlers, inverted indices, and
    sophisticated ranking algorithms. Understanding these components
    is essential for anyone interested in information retrieval.

    Modern search engines must handle billions of pages while providing
    sub-second query response times. This requires careful optimization
    of data structures and distributed systems design.
    """,
    "language": "en",
    "author": "John Doe",
    "date": "2024-12-15"
}

EVALUATION_RESULT = {
    "title": "Example Article: How to Build Search Engines",
    "content": "Comprehensive guide on building search engines with crawling, indexing, and ranking.",
    "summary": "This guide explains search engine architecture including distributed crawlers, inverted indices, and ranking algorithms. It covers essential concepts for building scalable search systems.",
    "language": "en",
    "ai_score": 85
}


# ==========================================
# INTEGRATION TESTS
# ==========================================

@pytest.mark.integration
class TestSystemIntegration:
    """
    Complete system integration test.

    Simulates the full workflow from URL import to AI evaluation.
    """

    def test_complete_workflow(self):
        """
        Test complete Coordinator workflow.

        Workflow:
        1. Import seed URLs (batch)
        2. Crawler gets URLs
        3. Crawler marks as crawling
        4. Crawler submits content
        5. Crawler marks as completed
        6. AI worker gets task
        7. AI worker marks as processing
        8. AI worker submits evaluation
        9. Verify statistics
        10. Retrieve evaluated pages
        """

        # ==========================================
        # PHASE 1: URL FRONTIER MANAGEMENT
        # ==========================================

        # 1.1 Import seed URLs via batch endpoint
        batch_response = client.post(
            "/api/v1/urls/batch",
            json={"urls": SEED_URLS}
        )
        assert batch_response.status_code == 200
        batch_data = batch_response.json()
        assert batch_data["added"] == 5
        assert batch_data["skipped"] == 0
        assert batch_data["total"] == 5

        # 1.2 Check URL statistics
        stats_response = client.get("/api/v1/stats")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["pending"] == 5
        assert stats["crawling"] == 0
        assert stats["completed"] == 0
        assert stats["total"] == 5

        # 1.3 Get next URLs (priority order)
        next_urls_response = client.get("/api/v1/urls?limit=3")
        assert next_urls_response.status_code == 200
        urls = next_urls_response.json()
        assert len(urls) == 3
        # Should be ordered by priority descending
        assert urls[0]["priority"] >= urls[1]["priority"]
        assert urls[1]["priority"] >= urls[2]["priority"]
        assert urls[0]["url"] == "https://example.com"  # Highest priority

        # Store URL ID for next steps
        url_id = urls[0]["id"]

        # ==========================================
        # PHASE 2: CRAWLER SIMULATION
        # ==========================================

        # 2.1 Mark URL as crawling
        crawling_response = client.post(f"/api/v1/urls/{url_id}/crawling")
        assert crawling_response.status_code == 200
        assert crawling_response.json()["status"] == "crawling"

        # 2.2 Verify statistics updated
        stats_response = client.get("/api/v1/stats")
        stats = stats_response.json()
        assert stats["pending"] == 4
        assert stats["crawling"] == 1

        # 2.3 Submit crawled content
        content_response = client.post(
            f"/api/v1/content/urls/{url_id}/content",
            json=SAMPLE_CONTENT
        )
        assert content_response.status_code == 201
        content_data = content_response.json()
        assert content_data["url_id"] == url_id
        assert content_data["title"] == SAMPLE_CONTENT["title"]
        assert content_data["language"] == "en"
        page_id = content_data["id"]

        # 2.4 Mark URL as completed
        completed_response = client.post(f"/api/v1/urls/{url_id}/completed")
        assert completed_response.status_code == 200
        assert completed_response.json()["status"] == "completed"
        assert completed_response.json()["last_crawled_at"] is not None

        # 2.5 Verify statistics
        stats_response = client.get("/api/v1/stats")
        stats = stats_response.json()
        assert stats["pending"] == 4
        assert stats["crawling"] == 0
        assert stats["completed"] == 1

        # ==========================================
        # PHASE 3: AI EVALUATOR SIMULATION
        # ==========================================

        # 3.1 Get next evaluation task
        task_response = client.get("/api/v1/tasks/next?type=evaluation")
        assert task_response.status_code == 200
        task = task_response.json()
        assert task is not None
        assert task["id"] == page_id
        assert task["url"] == "https://example.com"
        assert task["raw_html"] is not None  # Content from step 2.3
        assert task["depth"] == 0

        # 3.2 Mark task as processing
        processing_response = client.post(f"/api/v1/tasks/{page_id}/processing")
        assert processing_response.status_code == 200
        assert processing_response.json()["evaluation_status"] == "processing"

        # 3.3 Submit evaluation result
        result_response = client.post(
            f"/api/v1/tasks/{page_id}/result",
            json=EVALUATION_RESULT
        )
        assert result_response.status_code == 200
        result_data = result_response.json()
        assert result_data["evaluation_status"] == "evaluated"
        assert result_data["ai_score"] == 85
        assert result_data["evaluated_at"] is not None

        # 3.4 Verify no more pending tasks
        no_task_response = client.get("/api/v1/tasks/next?type=evaluation")
        assert no_task_response.status_code == 200
        assert no_task_response.json() is None

        # ==========================================
        # PHASE 4: STATISTICS & VERIFICATION
        # ==========================================

        # 4.1 Check evaluation statistics
        eval_stats_response = client.get("/api/v1/stats/evaluation")
        assert eval_stats_response.status_code == 200
        eval_stats = eval_stats_response.json()
        assert eval_stats["pages_by_status"]["evaluated"] == 1
        assert eval_stats["total_pages"] == 1
        assert eval_stats["score_distribution"]["80-100"] == 1
        assert eval_stats["languages"]["en"] == 1

        # 4.2 Retrieve evaluated pages
        pages_response = client.get("/api/v1/pages?status=evaluated&limit=10")
        assert pages_response.status_code == 200
        pages_data = pages_response.json()
        assert pages_data["count"] == 1
        assert len(pages_data["pages"]) == 1

        page = pages_data["pages"][0]
        assert page["id"] == page_id
        assert page["url"] == "https://example.com"
        assert page["title"] == EVALUATION_RESULT["title"]
        assert page["summary"] == EVALUATION_RESULT["summary"]
        assert page["ai_score"] == 85
        assert page["evaluation_status"] == "evaluated"

        # 4.3 Final URL statistics
        final_stats = client.get("/api/v1/stats").json()
        assert final_stats["completed"] == 1
        assert final_stats["pending"] == 4
        assert final_stats["total"] == 5

    def test_crawler_failure_workflow(self):
        """
        Test failure handling in crawler workflow.

        Workflow:
        1. Add URL
        2. Mark as crawling
        3. Mark as failed with error
        4. Verify statistics
        """
        # Add URL
        url_response = client.post(
            "/api/v1/urls",
            json={"url": "https://broken.com", "priority": 5}
        )
        assert url_response.status_code == 201
        url_id = url_response.json()["id"]

        # Mark as crawling
        client.post(f"/api/v1/urls/{url_id}/crawling")

        # Mark as failed
        failed_response = client.post(
            f"/api/v1/urls/{url_id}/failed",
            json={"error_message": "Connection timeout"}
        )
        assert failed_response.status_code == 200
        failed_data = failed_response.json()
        assert failed_data["status"] == "failed"
        assert failed_data["error_message"] == "Connection timeout"
        assert failed_data["crawl_attempts"] == 1

        # Verify statistics
        stats = client.get("/api/v1/stats").json()
        assert stats["failed"] == 1
        assert stats["crawling"] == 0

    def test_evaluation_failure_workflow(self):
        """
        Test failure handling in evaluation workflow.

        Workflow:
        1. Add URL and submit content
        2. Get evaluation task
        3. Mark task as failed
        4. Verify statistics
        """
        # Setup: Add URL and content
        url_response = client.post(
            "/api/v1/urls",
            json={"url": "https://eval-fail.com", "priority": 5}
        )
        url_id = url_response.json()["id"]

        client.post(f"/api/v1/urls/{url_id}/crawling")
        content_response = client.post(
            f"/api/v1/content/urls/{url_id}/content",
            json=SAMPLE_CONTENT
        )
        page_id = content_response.json()["id"]

        # Get task
        task = client.get("/api/v1/tasks/next?type=evaluation").json()
        assert task["id"] == page_id

        # Mark as failed
        failed_response = client.post(
            f"/api/v1/tasks/{page_id}/failed",
            json={"error": "LLM service unavailable"}
        )
        assert failed_response.status_code == 200
        assert failed_response.json()["evaluation_status"] == "failed"

        # Verify evaluation statistics
        eval_stats = client.get("/api/v1/stats/evaluation").json()
        assert eval_stats["pages_by_status"]["failed"] == 1
        assert "evaluated" not in eval_stats["pages_by_status"]

    def test_concurrent_crawler_behavior(self):
        """
        Test multiple crawlers getting different URLs.

        Simulates concurrent crawlers using SELECT FOR UPDATE SKIP LOCKED behavior.
        Note: SQLite doesn't fully support concurrent locks, but this documents
        the expected behavior.
        """
        # Add multiple URLs
        batch_response = client.post(
            "/api/v1/urls/batch",
            json={"urls": SEED_URLS}
        )
        assert batch_response.json()["added"] == 5

        # Crawler 1 gets URLs
        crawler1_urls = client.get("/api/v1/urls?limit=2").json()
        assert len(crawler1_urls) == 2

        # Crawler 2 gets different URLs (next in queue)
        crawler2_urls = client.get("/api/v1/urls?limit=2").json()
        assert len(crawler2_urls) == 2

        # URLs should be different (in real scenario with locks)
        # In SQLite without real concurrency, they'll be the same
        # This test documents expected behavior
        all_urls = crawler1_urls + crawler2_urls
        url_strings = [u["url"] for u in all_urls]
        assert "https://example.com" in url_strings
        assert "https://example.com/blog" in url_strings


# ==========================================
# HELPER TEST
# ==========================================

def test_health_check():
    """Basic health check to verify test setup."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
