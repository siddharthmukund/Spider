"""Test suite for /start endpoint."""
import pytest
from fastapi.testclient import TestClient
from webapp.main import app
import os


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_api_key(monkeypatch):
    """Mock API key for testing."""
    test_key = "test-api-key-12345"
    monkeypatch.setenv("WEBAPP_API_KEY", test_key)
    return test_key


@pytest.fixture
def auth_headers(mock_api_key):
    """Generate authentication headers."""
    return {"X-API-Key": mock_api_key}


class TestStartEndpoint:
    """Tests for crawl task creation endpoint."""

    def test_valid_payload_returns_task_id(self, client, auth_headers):
        """Test that a valid crawl request returns a task ID."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 10,
            "max_workers": 2
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert len(data["task_id"]) > 0

    def test_missing_api_key_returns_401(self, client):
        """Test that missing API key returns 401."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 10
        })
        assert response.status_code == 401

    def test_invalid_api_key_returns_403(self, client):
        """Test that invalid API key returns 403."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 10
        }, headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 403

    def test_missing_base_url_returns_422(self, client, auth_headers):
        """Test that missing base_url returns validation error."""
        response = client.post("/start", json={
            "max_pages": 100
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_localhost_url_blocked_for_ssrf(self, client, auth_headers):
        """Test that localhost URLs are blocked (SSRF protection)."""
        response = client.post("/start", json={
            "base_url": "http://localhost:8000",
            "max_pages": 10
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "blocked" in response.json()["detail"].lower()

    def test_private_ip_blocked_for_ssrf(self, client, auth_headers):
        """Test that private IP addresses are blocked (SSRF protection)."""
        response = client.post("/start", json={
            "base_url": "http://192.168.1.1",
            "max_pages": 10
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "blocked" in response.json()["detail"].lower()

    def test_metadata_endpoint_blocked_for_ssrf(self, client, auth_headers):
        """Test that cloud metadata endpoints are blocked."""
        response = client.post("/start", json={
            "base_url": "http://169.254.169.254/",
            "max_pages": 10
        }, headers=auth_headers)
        assert response.status_code == 400

    def test_invalid_url_scheme_returns_400(self, client, auth_headers):
        """Test that invalid URL scheme (not http/https) returns error."""
        response = client.post("/start", json={
            "base_url": "ftp://example.com",
            "max_pages": 100
        }, headers=auth_headers)
        assert response.status_code in [400, 422]

    def test_negative_max_pages_rejected(self, client, auth_headers):
        """Test that negative max_pages is rejected."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": -5
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_zero_max_pages_rejected(self, client, auth_headers):
        """Test that zero max_pages is rejected."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 0
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_excessive_max_pages_rejected(self, client, auth_headers):
        """Test that excessively large max_pages is rejected."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 100000
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_invalid_max_workers_rejected(self, client, auth_headers):
        """Test that invalid max_workers value is rejected."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 10,
            "max_workers": 0
        }, headers=auth_headers)
        assert response.status_code == 422

    @pytest.mark.parametrize("url", [
        "https://example.com/path",
        "http://test.example.org",
        "https://subdomain.example.com:8080/",
    ])
    def test_various_valid_urls_accepted(self, client, auth_headers, url):
        """Test that various valid URL formats are accepted."""
        response = client.post("/start", json={
            "base_url": url,
            "max_pages": 5
        }, headers=auth_headers)
        assert response.status_code == 200
