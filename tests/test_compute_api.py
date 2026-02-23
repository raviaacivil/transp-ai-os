"""Tests for /compute endpoints."""

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


class TestComputeSignalized:
    """Tests for POST /compute/signalized endpoint."""

    @pytest.mark.asyncio
    async def test_basic_computation(self, client):
        """Should compute LOS for valid minimal input."""
        payload = {
            "volume": 800,
            "num_lanes": 2,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["engine_version"] == __engine_version__
        assert data["volume"] == 800
        assert data["num_lanes"] == 2
        assert data["capacity"] > 0
        assert data["vc_ratio"] > 0
        assert data["control_delay"] > 0
        assert data["los"] in ["A", "B", "C", "D", "E", "F"]
        assert data["is_oversaturated"] is False
        assert "saturation_flow" in data

    @pytest.mark.asyncio
    async def test_full_input(self, client):
        """Should handle all optional parameters."""
        payload = {
            "volume": 850,
            "num_lanes": 2,
            "movement_type": "through",
            "base_saturation_flow": 1900,
            "lane_width": 11.0,
            "heavy_vehicle_pct": 8.0,
            "grade_pct": 2.0,
            "parking_adjacent": False,
            "parking_maneuvers_per_hour": 0,
            "bus_stops_per_hour": 5,
            "area_type": "other",
            "left_turn_pct": 0,
            "right_turn_pct": 0,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 42,
                "control_type": "pretimed"
            },
            "analysis_period_hours": 0.25,
            "upstream_filtering_factor": 1.0
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["volume"] == 850
        sat_flow = data["saturation_flow"]
        assert sat_flow["f_hv"] < 1.0  # Heavy vehicles applied
        assert sat_flow["f_g"] < 1.0   # Grade applied
        assert sat_flow["f_bb"] < 1.0  # Bus blockage applied

    @pytest.mark.asyncio
    async def test_undersaturated_condition(self, client):
        """Should identify undersaturated v/c < 1."""
        payload = {
            "volume": 400,
            "num_lanes": 2,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 45
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["vc_ratio"] < 1.0
        assert data["is_oversaturated"] is False
        assert data["los"] in ["A", "B", "C"]

    @pytest.mark.asyncio
    async def test_oversaturated_condition(self, client):
        """Should identify oversaturated v/c > 1."""
        payload = {
            "volume": 2500,
            "num_lanes": 2,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 35
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["vc_ratio"] > 1.0
        assert data["is_oversaturated"] is True
        assert data["los"] in ["E", "F"]

    @pytest.mark.asyncio
    async def test_cbd_area_type(self, client):
        """Should apply CBD area factor of 0.90."""
        payload = {
            "volume": 800,
            "num_lanes": 2,
            "area_type": "cbd",
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["saturation_flow"]["f_a"] == 0.9

    @pytest.mark.asyncio
    async def test_left_turn_movement(self, client):
        """Should apply left turn factor for exclusive left lane."""
        payload = {
            "volume": 300,
            "num_lanes": 1,
            "movement_type": "left",
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 20
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["saturation_flow"]["f_lt"] == 0.95

    @pytest.mark.asyncio
    async def test_actuated_coordinated_control(self, client):
        """Should accept actuated coordinated control type."""
        payload = {
            "volume": 800,
            "num_lanes": 2,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40,
                "control_type": "actuated_coordinated"
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_saturation_flow_breakdown(self, client):
        """Should include all saturation flow adjustment factors."""
        payload = {
            "volume": 800,
            "num_lanes": 2,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 200

        sat_flow = response.json()["saturation_flow"]
        required_factors = [
            "base_saturation_flow",
            "adjusted_saturation_flow",
            "total_saturation_flow",
            "f_w", "f_hv", "f_g", "f_p", "f_bb", "f_a", "f_lt", "f_rt"
        ]
        for factor in required_factors:
            assert factor in sat_flow


class TestComputeSignalizedValidation:
    """Validation tests for /compute/signalized."""

    @pytest.mark.asyncio
    async def test_negative_volume_rejected(self, client):
        """Should reject negative volume."""
        payload = {
            "volume": -100,
            "num_lanes": 2,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_zero_lanes_rejected(self, client):
        """Should reject zero lanes."""
        payload = {
            "volume": 800,
            "num_lanes": 0,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_green_exceeds_cycle_rejected(self, client):
        """Should reject effective green > cycle length."""
        payload = {
            "volume": 800,
            "num_lanes": 2,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 100
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_area_type_rejected(self, client):
        """Should reject invalid area type."""
        payload = {
            "volume": 800,
            "num_lanes": 2,
            "area_type": "downtown",
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_signal_timing_rejected(self, client):
        """Should reject missing signal timing."""
        payload = {
            "volume": 800,
            "num_lanes": 2
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_heavy_vehicle_pct_over_100_rejected(self, client):
        """Should reject heavy vehicle percent > 100."""
        payload = {
            "volume": 800,
            "num_lanes": 2,
            "heavy_vehicle_pct": 150,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_lane_width_too_narrow_rejected(self, client):
        """Should reject lane width <= 8 feet."""
        payload = {
            "volume": 800,
            "num_lanes": 2,
            "lane_width": 7.0,
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

        response = await client.post("/compute/signalized", json=payload)
        assert response.status_code == 422
