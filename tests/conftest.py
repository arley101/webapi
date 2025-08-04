# tests/conftest.py
"""
Pytest configuration and shared fixtures for EliteDynamicsAPI tests.
"""

import os
import pytest
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Set test environment
os.environ["ENVIRONMENT"] = "testing"

# Import after setting environment
from app.main import app
from app.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Create a test client for synchronous API testing.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async test client for asynchronous API testing.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_settings():
    """
    Provide mock settings for testing.
    """
    return {
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "DEBUG",
        "APP_NAME": "EliteDynamicsAPI",
        "APP_VERSION": "1.1.0"
    }


@pytest.fixture
def sample_correlation_id():
    """
    Provide a sample correlation ID for testing.
    """
    return "test-correlation-id-12345"


@pytest.fixture
def sample_request_headers():
    """
    Provide sample request headers for testing.
    """
    return {
        "Content-Type": "application/json",
        "User-Agent": "EliteDynamicsAPI-Test/1.0",
        "X-Correlation-ID": "test-correlation-id"
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Setup test environment before running tests.
    """
    # Ensure we're in test mode
    assert settings.ENVIRONMENT == "testing"
    print(f"Running tests in {settings.ENVIRONMENT} environment")
    
    yield
    
    # Cleanup after tests
    print("Test environment cleanup completed")


class TestData:
    """
    Container for test data constants.
    """
    
    VALID_ACTION_REQUEST = {
        "action": "test_action",
        "parameters": {
            "test_param": "test_value"
        }
    }
    
    INVALID_ACTION_REQUEST = {
        "action": "",
        "parameters": {}
    }
    
    SAMPLE_USER_CONTEXT = {
        "user_id": "test-user-123",
        "tenant_id": "test-tenant-456"
    }


@pytest.fixture
def test_data():
    """
    Provide test data for tests.
    """
    return TestData()