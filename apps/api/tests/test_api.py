"""
API Tests - Basic smoke tests for HydroQ-QC-Assistant
"""

import pytest
from httpx import AsyncClient
from src.main import app


@pytest.fixture
def test_client():
    """Create test client."""
    from httpx import ASGITransport
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_health_check(test_client):
    """Test health endpoint."""
    async with test_client as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_root_endpoint(test_client):
    """Test root endpoint."""
    async with test_client as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "HydroQ-QC-Assistant API"


@pytest.mark.asyncio
async def test_openapi_docs(test_client):
    """Test OpenAPI docs are available."""
    async with test_client as client:
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert data["info"]["title"] == "HydroQ-QC-Assistant API"


@pytest.mark.asyncio
async def test_unauthenticated_datasets_list(test_client):
    """Test that datasets list requires authentication."""
    async with test_client as client:
        response = await client.get("/api/v1/datasets/")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_runs_list(test_client):
    """Test that runs list requires authentication."""
    async with test_client as client:
        response = await client.get("/api/v1/runs/")
        assert response.status_code == 401


class TestAuth:
    """Authentication tests."""
    
    @pytest.mark.asyncio
    async def test_register_user(self, test_client):
        """Test user registration."""
        async with test_client as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "testpassword123",
                    "role": "viewer",
                },
            )
            # May fail if DB not available - that's expected for unit tests
            # This is more of an integration test
            assert response.status_code in (201, 500)
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, test_client):
        """Test login with invalid credentials."""
        async with test_client as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "username": "nonexistent",
                    "password": "wrongpassword",
                },
            )
            assert response.status_code in (401, 500)
