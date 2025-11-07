"""
Shared Test Fixtures for All Test Modules
Provides common fixtures for FastAPI testing, mocking, and test data.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


@pytest.fixture(scope="session")
def test_app():
    """
    Create FastAPI test application (session-scoped).

    Returns:
        FastAPI: Application instance for testing
    """
    from backend.main import app
    return app


@pytest.fixture
def client(test_app):
    """
    Create FastAPI test client.

    Args:
        test_app: FastAPI application fixture

    Returns:
        TestClient: HTTP test client
    """
    return TestClient(test_app)


@pytest.fixture
def mock_ollama():
    """
    Mock Ollama API for all tests.

    Returns:
        Mock: Configured Ollama mock
    """
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': '{"response_to_user": "Test response", "needs_approval": false, "delegation_plan": []}'
        }
        mock_post.return_value = mock_response
        yield mock_post


@pytest.fixture
def mock_comfyui():
    """
    Mock ComfyUI API for all tests.

    Returns:
        Dict: Mocks for GET and POST requests
    """
    with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
        # Mock system stats
        mock_stats = Mock()
        mock_stats.status_code = 200
        mock_stats.json.return_value = {
            'system': {'os': 'linux'},
            'devices': [{'type': 'cpu'}],
            'queue_remaining': 0
        }

        # Mock prompt submission
        mock_prompt = Mock()
        mock_prompt.status_code = 200
        mock_prompt.json.return_value = {
            'prompt_id': 'test_prompt_123'
        }

        mock_get.return_value = mock_stats
        mock_post.return_value = mock_prompt

        yield {'get': mock_get, 'post': mock_post}


@pytest.fixture
def mock_api_key():
    """
    Mock API key for testing protected endpoints.

    Returns:
        str: Test API key
    """
    return "test_api_key_12345678901234567890123456789012"


@pytest.fixture
def auth_headers(mock_api_key):
    """
    Authentication headers for testing.

    Args:
        mock_api_key: API key fixture

    Returns:
        Dict: Headers with API key
    """
    return {"X-API-Key": mock_api_key}


@pytest.fixture
def sample_prompt_request():
    """
    Sample prompt request payload.

    Returns:
        Dict: Valid prompt request
    """
    return {
        "message": "Create a knight sprite",
        "session_id": "test_session_123"
    }


@pytest.fixture
def sample_execution_request():
    """
    Sample execution request payload.

    Returns:
        Dict: Valid execution request
    """
    return {
        "plan": [
            {
                "department": "Art",
                "task": "Generate knight sprite with 8 frames",
                "details": {"style": "pixel art", "resolution": "32x32"}
            }
        ],
        "session_id": "test_session_123"
    }


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """
    Reset rate limiter between tests.

    Automatically applied to all tests.
    """
    from backend.security import rate_limiter
    rate_limiter.buckets.clear()
    yield
    rate_limiter.buckets.clear()


@pytest.fixture(scope="session")
def temp_test_dir(tmp_path_factory):
    """
    Create temporary directory for test files.

    Args:
        tmp_path_factory: Pytest temporary path factory

    Returns:
        Path: Temporary directory path
    """
    return tmp_path_factory.mktemp("test_data")


@pytest.fixture
def mock_logger():
    """
    Mock logger for testing logging calls.

    Returns:
        Mock: Logger mock
    """
    with patch('backend.dependencies.logger') as mock_log:
        yield mock_log


# Pytest configuration hooks

def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line(
        "markers", "integration: integration tests requiring external services"
    )
    config.addinivalue_line(
        "markers", "slow: slow-running tests"
    )
    config.addinivalue_line(
        "markers", "security: security-related tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip integration tests by default."""
    skip_integration = pytest.mark.skip(reason="Integration tests require --run-integration flag")

    for item in items:
        if "integration" in item.keywords and not config.getoption("--run-integration", default=False):
            item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires services)"
    )
