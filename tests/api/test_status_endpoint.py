"""Test suite for /status endpoint."""
import pytest
from fastapi.testclient import TestClient
from webapp.main import app, TASKS


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
    from webapp.store import add_user, load_users
    from webapp.security.auth import get_password_hash
    username = "testuser"
    password = "secret"
    hashed = get_password_hash(password)
    users = load_users()
    users.pop(username, None)
    add_user(username, hashed, scopes=["*"], is_active=True)
    return {"username": username, "password": password}


@pytest.fixture
def auth_headers(create_user):
    from fastapi.testclient import TestClient
    from webapp.main import app
    client = TestClient(app)
    resp = client.post("/token", data={"username": create_user["username"], "password": create_user["password"]})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api_key_headers(mock_api_key):
    """Generate headers using the mocked environment API key."""
    return {"X-API-Key": mock_api_key}


@pytest.fixture
def sample_task_id():
    """Create a sample task for testing."""
    import asyncio
    task_id = "test-task-123"
    TASKS[task_id] = {
        'id': task_id,
        'status': 'running',
        'queue': asyncio.Queue(),
        'report': None,
        'cache_stats': None,
        'started_at': None,
        'finished_at': None,
        'base_url': 'https://example.com',
        'max_pages': 10,
        'max_workers': 2,
        'output_dir': '/tmp/test',
        'created_at': 1234567890.0
    }
    yield task_id
    # Cleanup
    if task_id in TASKS:
        del TASKS[task_id]


class TestStatusEndpoint:
    """Tests for task status endpoint."""

    def test_get_status_existing_task(self, client, auth_headers, sample_task_id):
        """Test retrieving status of an existing task."""
        response = client.get(f"/status/{sample_task_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == sample_task_id
        assert data['status'] == 'running'

    def test_get_status_nonexistent_task(self, client, auth_headers):
        """Test retrieving status of a non-existent task."""
        response = client.get("/status/nonexistent-task-id", headers=auth_headers)
        assert response.status_code == 404
        assert 'not found' in response.json()['detail'].lower()

    def test_status_includes_progress_info(self, client, auth_headers, sample_task_id):
        """Test that status response includes expected fields."""
        response = client.get(f"/status/{sample_task_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert 'id' in data
        assert 'status' in data
    
    def test_status_without_auth_returns_401(self, client, sample_task_id):
        """Test that status endpoint requires authentication."""
        response = client.get(f"/status/{sample_task_id}")
        assert response.status_code == 401

    def test_status_with_api_key_fallback(self, client, api_key_headers, sample_task_id):
        """Verify that legacy API key still works for status."""
        response = client.get(f"/status/{sample_task_id}", headers=api_key_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'running'
