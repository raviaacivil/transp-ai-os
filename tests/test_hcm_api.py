"""Tests for HCM API endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from src.hcm_engine import __engine_version__


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestEngineInfo:
    """Tests for /hcm/info endpoint."""

    @pytest.mark.asyncio
    async def test_get_engine_info(self, client):
        """Should return engine version and description."""
        response = await client.get("/hcm/info")
        assert response.status_code == 200

        data = response.json()
        assert data["engine_version"] == __engine_version__
        assert "HCM" in data["description"]


class TestComputeLOS:
    """Tests for /hcm/compute-los endpoint."""

    @pytest.mark.asyncio
    async def test_compute_los_basic(self, client):
        """Should compute LOS for valid input."""
        payload = {
            "lane_group": {
                "volume": 800,
                "num_lanes": 2,
                "signal_timing": {
                    "cycle_length": 90,
                    "effective_green": 40
                }
            }
        }

        response = await client.post("/hcm/compute-los", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert "result" in data

        result = data["result"]
        assert result["engine_version"] == __engine_version__
        assert result["volume"] == 800
        assert result["num_lanes"] == 2
        assert result["capacity"] > 0
        assert result["vc_ratio"] > 0
        assert result["control_delay"] > 0
        assert result["los"] in ["A", "B", "C", "D", "E", "F"]

    @pytest.mark.asyncio
    async def test_compute_los_undersaturated(self, client):
        """Should correctly identify undersaturated condition."""
        payload = {
            "lane_group": {
                "volume": 400,
                "num_lanes": 2,
                "signal_timing": {
                    "cycle_length": 90,
                    "effective_green": 40
                }
            }
        }

        response = await client.post("/hcm/compute-los", json=payload)
        assert response.status_code == 200

        result = response.json()["result"]
        assert result["vc_ratio"] < 1.0
        assert result["is_oversaturated"] is False

    @pytest.mark.asyncio
    async def test_compute_los_oversaturated(self, client):
        """Should correctly identify oversaturated condition."""
        payload = {
            "lane_group": {
                "volume": 2500,
                "num_lanes": 2,
                "signal_timing": {
                    "cycle_length": 90,
                    "effective_green": 40
                }
            }
        }

        response = await client.post("/hcm/compute-los", json=payload)
        assert response.status_code == 200

        result = response.json()["result"]
        assert result["vc_ratio"] > 1.0
        assert result["is_oversaturated"] is True
        assert result["los"] in ["E", "F"]

    @pytest.mark.asyncio
    async def test_compute_los_with_adjustments(self, client):
        """Should apply adjustment factors correctly."""
        payload = {
            "lane_group": {
                "volume": 800,
                "num_lanes": 2,
                "heavy_vehicle_pct": 15,
                "grade_pct": 3,
                "area_type": "cbd",
                "signal_timing": {
                    "cycle_length": 90,
                    "effective_green": 40
                }
            }
        }

        response = await client.post("/hcm/compute-los", json=payload)
        assert response.status_code == 200

        result = response.json()["result"]
        sat_flow = result["saturation_flow"]

        # Verify adjustment factors are applied
        assert sat_flow["f_hv"] < 1.0
        assert sat_flow["f_g"] < 1.0
        assert sat_flow["f_a"] == 0.9

    @pytest.mark.asyncio
    async def test_compute_los_includes_delay_breakdown(self, client):
        """Should include delay component breakdown."""
        payload = {
            "lane_group": {
                "volume": 800,
                "num_lanes": 2,
                "signal_timing": {
                    "cycle_length": 90,
                    "effective_green": 40
                }
            }
        }

        response = await client.post("/hcm/compute-los", json=payload)
        assert response.status_code == 200

        result = response.json()["result"]
        assert "uniform_delay" in result
        assert "incremental_delay" in result
        assert "control_delay" in result
        assert result["uniform_delay"] >= 0
        assert result["incremental_delay"] >= 0

    @pytest.mark.asyncio
    async def test_compute_los_invalid_volume(self, client):
        """Should reject negative volume."""
        payload = {
            "lane_group": {
                "volume": -100,
                "num_lanes": 2,
                "signal_timing": {
                    "cycle_length": 90,
                    "effective_green": 40
                }
            }
        }

        response = await client.post("/hcm/compute-los", json=payload)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_compute_los_invalid_green_exceeds_cycle(self, client):
        """Should reject effective green exceeding cycle length."""
        payload = {
            "lane_group": {
                "volume": 800,
                "num_lanes": 2,
                "signal_timing": {
                    "cycle_length": 90,
                    "effective_green": 100
                }
            }
        }

        response = await client.post("/hcm/compute-los", json=payload)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_compute_los_missing_required_fields(self, client):
        """Should reject missing required fields."""
        payload = {
            "lane_group": {
                "volume": 800
                # Missing num_lanes and signal_timing
            }
        }

        response = await client.post("/hcm/compute-los", json=payload)
        assert response.status_code == 422  # Validation error
