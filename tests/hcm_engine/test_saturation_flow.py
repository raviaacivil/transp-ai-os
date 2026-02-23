"""
Tests for saturation flow calculations.

Tests verify HCM 6th Edition equations and edge cases.
"""

import pytest
from src.hcm_engine.saturation_flow import (
    compute_lane_width_factor,
    compute_heavy_vehicle_factor,
    compute_grade_factor,
    compute_parking_factor,
    compute_bus_blockage_factor,
    compute_area_type_factor,
    compute_left_turn_factor,
    compute_right_turn_factor,
    compute_saturation_flow,
)
from src.hcm_engine.models import (
    LaneGroupInput,
    SignalTimingInput,
    MovementType,
)


class TestLaneWidthFactor:
    """Tests for lane width adjustment factor."""

    def test_standard_12ft_lane(self):
        """12-foot lane should have factor of 1.0."""
        assert compute_lane_width_factor(12.0) == 1.0

    def test_narrow_10ft_lane(self):
        """Narrow lane reduces saturation flow."""
        fw = compute_lane_width_factor(10.0)
        assert fw < 1.0
        assert fw == pytest.approx(0.9333, rel=0.01)

    def test_wide_14ft_lane(self):
        """Wide lane increases saturation flow."""
        fw = compute_lane_width_factor(14.0)
        assert fw > 1.0
        assert fw == pytest.approx(1.0667, rel=0.01)

    def test_minimum_bound(self):
        """Very narrow lane is bounded at 0.87."""
        fw = compute_lane_width_factor(8.0)
        assert fw == 0.87

    def test_maximum_bound(self):
        """Very wide lane is bounded at 1.07."""
        fw = compute_lane_width_factor(20.0)
        assert fw == 1.07


class TestHeavyVehicleFactor:
    """Tests for heavy vehicle adjustment factor."""

    def test_no_heavy_vehicles(self):
        """No heavy vehicles should have factor of 1.0."""
        assert compute_heavy_vehicle_factor(0.0) == 1.0

    def test_typical_heavy_vehicles(self):
        """5% heavy vehicles is common urban condition."""
        fhv = compute_heavy_vehicle_factor(5.0)
        assert fhv < 1.0
        assert fhv == pytest.approx(0.9524, rel=0.01)

    def test_high_heavy_vehicles(self):
        """20% heavy vehicles significantly reduces saturation."""
        fhv = compute_heavy_vehicle_factor(20.0)
        assert fhv == pytest.approx(0.8333, rel=0.01)

    def test_all_heavy_vehicles(self):
        """100% heavy vehicles (edge case)."""
        fhv = compute_heavy_vehicle_factor(100.0)
        assert fhv == pytest.approx(0.5, rel=0.01)


class TestGradeFactor:
    """Tests for grade adjustment factor."""

    def test_level_grade(self):
        """Level grade (0%) should have factor of 1.0."""
        assert compute_grade_factor(0.0) == 1.0

    def test_uphill_grade(self):
        """Uphill grade reduces saturation flow."""
        fg = compute_grade_factor(4.0)
        assert fg < 1.0
        assert fg == pytest.approx(0.98, rel=0.01)

    def test_downhill_grade(self):
        """Downhill grade increases saturation flow."""
        fg = compute_grade_factor(-4.0)
        assert fg > 1.0
        assert fg == pytest.approx(1.02, rel=0.01)

    def test_steep_uphill(self):
        """Steep uphill (10%)."""
        fg = compute_grade_factor(10.0)
        assert fg == pytest.approx(0.95, rel=0.01)

    def test_steep_downhill(self):
        """Steep downhill (-10%)."""
        fg = compute_grade_factor(-10.0)
        assert fg == pytest.approx(1.05, rel=0.01)


class TestParkingFactor:
    """Tests for parking adjustment factor."""

    def test_no_parking(self):
        """No parking should have factor of 1.0."""
        assert compute_parking_factor(False, 0, 2) == 1.0

    def test_parking_adjacent_no_maneuvers(self):
        """Parking adjacent but no maneuvers."""
        assert compute_parking_factor(True, 0, 2) == 1.0

    def test_parking_with_maneuvers(self):
        """Parking maneuvers reduce saturation flow."""
        fp = compute_parking_factor(True, 10, 2)
        assert fp < 1.0

    def test_high_parking_activity(self):
        """High parking activity."""
        fp = compute_parking_factor(True, 30, 1)
        assert fp < 0.9

    def test_minimum_bound(self):
        """Factor cannot go below 0.05."""
        fp = compute_parking_factor(True, 1000, 1)
        assert fp == 0.05


class TestBusBlockageFactor:
    """Tests for bus blockage adjustment factor."""

    def test_no_buses(self):
        """No bus stops should have factor of 1.0."""
        assert compute_bus_blockage_factor(0, 2) == 1.0

    def test_typical_bus_activity(self):
        """Typical bus stopping activity."""
        fbb = compute_bus_blockage_factor(10, 2)
        assert fbb < 1.0
        assert fbb > 0.9

    def test_high_bus_activity(self):
        """High bus activity reduces saturation flow."""
        fbb = compute_bus_blockage_factor(50, 1)
        assert fbb < 0.9


class TestAreaTypeFactor:
    """Tests for area type adjustment factor."""

    def test_cbd_area(self):
        """CBD areas have 0.90 factor."""
        assert compute_area_type_factor("cbd") == 0.90
        assert compute_area_type_factor("CBD") == 0.90

    def test_other_area(self):
        """Non-CBD areas have 1.0 factor."""
        assert compute_area_type_factor("other") == 1.0
        assert compute_area_type_factor("suburban") == 1.0


class TestLeftTurnFactor:
    """Tests for left turn adjustment factor."""

    def test_through_movement(self):
        """Through-only movement has factor of 1.0."""
        flt = compute_left_turn_factor(MovementType.THROUGH, 0)
        assert flt == 1.0

    def test_exclusive_left_turn(self):
        """Exclusive left turn lane has factor of 0.95."""
        flt = compute_left_turn_factor(MovementType.LEFT, 100)
        assert flt == 0.95

    def test_shared_lane_with_lefts(self):
        """Shared lane with left turns."""
        flt = compute_left_turn_factor(MovementType.THROUGH_LEFT, 20)
        assert flt < 1.0
        assert flt > 0.9


class TestRightTurnFactor:
    """Tests for right turn adjustment factor."""

    def test_through_movement(self):
        """Through-only movement has factor of 1.0."""
        frt = compute_right_turn_factor(MovementType.THROUGH, 0)
        assert frt == 1.0

    def test_exclusive_right_turn(self):
        """Exclusive right turn lane has factor of 0.85."""
        frt = compute_right_turn_factor(MovementType.RIGHT, 100)
        assert frt == 0.85

    def test_shared_lane_with_rights(self):
        """Shared lane with right turns."""
        frt = compute_right_turn_factor(MovementType.THROUGH_RIGHT, 20)
        assert frt < 1.0
        assert frt > 0.9


class TestComputeSaturationFlow:
    """Integration tests for saturation flow calculation."""

    @pytest.fixture
    def base_inputs(self):
        """Base lane group inputs with default values."""
        return LaneGroupInput(
            volume=800,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )

    def test_base_saturation_flow(self, base_inputs):
        """Test with all default adjustment factors."""
        result = compute_saturation_flow(base_inputs)

        # With all defaults, adjusted should equal base
        assert result.base_saturation_flow == 1900.0
        assert result.adjusted_saturation_flow == pytest.approx(1900.0, rel=0.01)
        assert result.total_saturation_flow == pytest.approx(3800.0, rel=0.01)

        # All factors should be 1.0
        assert result.f_w == 1.0
        assert result.f_hv == 1.0
        assert result.f_g == 1.0
        assert result.f_a == 1.0

    def test_with_adjustments(self):
        """Test with multiple adjustment factors applied."""
        inputs = LaneGroupInput(
            volume=800,
            num_lanes=2,
            lane_width=11.0,
            heavy_vehicle_pct=10.0,
            grade_pct=2.0,
            area_type="cbd",
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_saturation_flow(inputs)

        # All adjustment factors should reduce saturation flow
        assert result.f_w < 1.0
        assert result.f_hv < 1.0
        assert result.f_g < 1.0
        assert result.f_a < 1.0

        # Total should be significantly less than base
        assert result.adjusted_saturation_flow < 1900.0
        assert result.total_saturation_flow < 3800.0

    def test_single_lane(self):
        """Test single lane calculation."""
        inputs = LaneGroupInput(
            volume=400,
            num_lanes=1,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_saturation_flow(inputs)

        assert result.total_saturation_flow == result.adjusted_saturation_flow
