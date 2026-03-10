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
    """Mock environment API key for backward compatibility tests."""
    test_key = "test-api-key-12345"
    monkeypatch.setenv("WEBAPP_API_KEY", test_key)
    return test_key


@pytest.fixture
def create_user():
    """Create a user in the JSON store and return credentials."""
    from webapp.store import add_user, load_users
    from webapp.security.auth import get_password_hash
    username = "testuser"
    password = "secret"
    hashed = get_password_hash(password)
    # clear existing
    users = load_users()
    users.pop(username, None)
    add_user(username, hashed, scopes=["*"], is_active=True)
    return {"username": username, "password": password}


@pytest.fixture
def jwt_auth_headers(create_user):
    """Generate authentication headers using JWT token."""
    # obtain token via /token
    from fastapi.testclient import TestClient
    from webapp.main import app
    client = TestClient(app)
    resp = client.post("/token", data={"username": create_user["username"], "password": create_user["password"]})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# legacy API key fixture retained for targeted tests
@pytest.fixture
def api_key_headers(mock_api_key):
    """Generate authentication headers using environment API key."""
    return {"X-API-Key": mock_api_key}


class TestStartEndpoint:
    """Tests for crawl task creation endpoint."""

    def test_valid_payload_returns_task_id(self, client, jwt_auth_headers):
        """Test that a valid crawl request returns a task ID."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 10,
            "max_workers": 2
        }, headers=jwt_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert len(data["task_id"]) > 0

    def test_token_endpoint_issues_jwt(self, client, create_user):
        """Requesting a token with correct credentials returns bearer token."""
        resp = client.post("/token", data={
            "username": create_user["username"],
            "password": create_user["password"]
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        tok = resp.json()["access_token"]
        assert tok.count(".") == 2  # basic JWT structure check

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

    def test_api_key_fallback_still_works(self, client, api_key_headers):
        """Legacy API key header should still authenticate a request."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 5
        }, headers=api_key_headers)
        assert response.status_code == 200
        assert "task_id" in response.json()

    def test_missing_base_url_returns_422(self, client, jwt_auth_headers):
        """Test that missing base_url returns validation error."""
        response = client.post("/start", json={
            "max_pages": 100
        }, headers=jwt_auth_headers)
        assert response.status_code == 422

    def test_localhost_url_blocked_for_ssrf(self, client, jwt_auth_headers):
        """Test that localhost URLs are blocked (SSRF protection)."""
        response = client.post("/start", json={
            "base_url": "http://localhost:8000",
            "max_pages": 10
        }, headers=jwt_auth_headers)
        assert response.status_code == 400
        assert "blocked" in response.json()["detail"].lower()

    def test_private_ip_blocked_for_ssrf(self, client, jwt_auth_headers):
        """Test that private IP addresses are blocked (SSRF protection)."""
        response = client.post("/start", json={
            "base_url": "http://192.168.1.1",
            "max_pages": 10
        }, headers=jwt_auth_headers)
        assert response.status_code == 400
        assert "blocked" in response.json()["detail"].lower()

    def test_metadata_endpoint_blocked_for_ssrf(self, client, jwt_auth_headers):
        """Test that cloud metadata endpoints are blocked."""
        response = client.post("/start", json={
            "base_url": "http://169.254.169.254/",
            "max_pages": 10
        }, headers=jwt_auth_headers)
        assert response.status_code == 400

    def test_allowlist_bypasses_ssrf(self, client, jwt_auth_headers, monkeypatch):
        """URLs listed in SSRF_ALLOWED_HOSTS should skip validation."""
        monkeypatch.setenv("SSRF_ALLOWED_HOSTS", "test.example.org")
        response = client.post("/start", json={
            "base_url": "http://test.example.org",
            "max_pages": 1
        }, headers=jwt_auth_headers)
        assert response.status_code == 200

    def test_invalid_url_scheme_returns_400(self, client, jwt_auth_headers):
        """Test that invalid URL scheme (not http/https) returns error."""
        response = client.post("/start", json={
            "base_url": "ftp://example.com",
            "max_pages": 100
        }, headers=jwt_auth_headers)
        assert response.status_code in [400, 422]

    def test_negative_max_pages_rejected(self, client, jwt_auth_headers):
        """Test that negative max_pages is rejected."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": -5
        }, headers=jwt_auth_headers)
        assert response.status_code == 422

    def test_zero_max_pages_rejected(self, client, jwt_auth_headers):
        """Test that zero max_pages is rejected."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 0
        }, headers=jwt_auth_headers)
        assert response.status_code == 422

    def test_excessive_max_pages_rejected(self, client, jwt_auth_headers):
        """Test that excessively large max_pages is rejected."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 100000
        }, headers=jwt_auth_headers)
        assert response.status_code == 422

    def test_invalid_max_workers_rejected(self, client, jwt_auth_headers):
        """Test that invalid max_workers value is rejected."""
        response = client.post("/start", json={
            "base_url": "https://example.com",
            "max_pages": 10,
            "max_workers": 0
        }, headers=jwt_auth_headers)
        assert response.status_code == 422

    @pytest.mark.parametrize("url", [
        "https://example.com/path",
        "http://test.example.org",
        "https://subdomain.example.com:8080/",
    ])
    def test_various_valid_urls_accepted(self, client, jwt_auth_headers, url):
        """Test that various valid URL formats are accepted."""
        response = client.post("/start", json={
            "base_url": url,
            "max_pages": 5
        }, headers=jwt_auth_headers)
        assert response.status_code == 200
