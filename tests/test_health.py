"""Health endpoint tests."""

import pytest

from app import __version__


@pytest.mark.asyncio
async def test_health_check(client):
    """Test basic health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__
