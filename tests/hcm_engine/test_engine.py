"""
Integration tests for the HCM signalized intersection engine.

Tests the complete calculation pipeline from inputs to results.
"""

import pytest
from src.hcm_engine import (
    compute_lane_group_results,
    LaneGroupInput,
    SignalTimingInput,
    LevelOfService,
    __engine_version__,
)
from src.hcm_engine.models import MovementType, SignalControlType


class TestEngineBasic:
    """Basic engine functionality tests."""

    @pytest.fixture
    def typical_inputs(self):
        """Typical lane group inputs for a major approach."""
        return LaneGroupInput(
            volume=800,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )

    def test_returns_result_object(self, typical_inputs):
        """Engine should return a LaneGroupResult."""
        result = compute_lane_group_results(typical_inputs)
        assert result is not None
        assert hasattr(result, "los")
        assert hasattr(result, "control_delay")
        assert hasattr(result, "capacity")
        assert hasattr(result, "vc_ratio")

    def test_engine_version_included(self, typical_inputs):
        """Result should include engine version."""
        result = compute_lane_group_results(typical_inputs)
        assert result.engine_version == __engine_version__
        assert "HCM6" in result.engine_version

    def test_input_echoed(self, typical_inputs):
        """Result should echo key inputs for audit."""
        result = compute_lane_group_results(typical_inputs)
        assert result.volume == typical_inputs.volume
        assert result.num_lanes == typical_inputs.num_lanes

    def test_saturation_flow_included(self, typical_inputs):
        """Result should include saturation flow breakdown."""
        result = compute_lane_group_results(typical_inputs)
        assert result.saturation_flow is not None
        assert result.saturation_flow.base_saturation_flow > 0
        assert result.saturation_flow.total_saturation_flow > 0

    def test_capacity_positive(self, typical_inputs):
        """Capacity should be positive."""
        result = compute_lane_group_results(typical_inputs)
        assert result.capacity > 0

    def test_delay_positive(self, typical_inputs):
        """Control delay should be positive."""
        result = compute_lane_group_results(typical_inputs)
        assert result.control_delay > 0
        assert result.uniform_delay > 0
        assert result.incremental_delay >= 0


class TestEngineUndersaturated:
    """Tests for undersaturated conditions (v/c < 1)."""

    def test_low_volume(self):
        """Low volume should result in undersaturated condition."""
        inputs = LaneGroupInput(
            volume=400,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.vc_ratio < 1.0
        assert result.is_oversaturated is False
        assert result.los in [LevelOfService.A, LevelOfService.B, LevelOfService.C]

    def test_moderate_volume(self):
        """Moderate volume should still be undersaturated."""
        inputs = LaneGroupInput(
            volume=800,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.vc_ratio < 1.0
        assert result.is_oversaturated is False

    def test_high_green_helps(self):
        """More green time should improve LOS."""
        inputs_low = LaneGroupInput(
            volume=800,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=30
            )
        )
        inputs_high = LaneGroupInput(
            volume=800,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=50
            )
        )

        result_low = compute_lane_group_results(inputs_low)
        result_high = compute_lane_group_results(inputs_high)

        assert result_high.vc_ratio < result_low.vc_ratio
        assert result_high.control_delay < result_low.control_delay


class TestEngineAtCapacity:
    """Tests for at-capacity conditions (v/c = 1)."""

    def test_near_capacity(self):
        """Volume near capacity should have v/c close to 1."""
        # First, find capacity with given timing
        inputs = LaneGroupInput(
            volume=1000,  # Placeholder
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        # Now set volume to capacity
        capacity = result.capacity
        inputs_at_cap = LaneGroupInput(
            volume=capacity,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result_at_cap = compute_lane_group_results(inputs_at_cap)

        assert result_at_cap.vc_ratio == pytest.approx(1.0, rel=0.01)

    def test_at_capacity_los(self):
        """At capacity should typically be LOS D or E."""
        # Approximate capacity for 2 lanes, 40/90 g/C
        # s = 1900 * 2 = 3800, c = 3800 * 40/90 ≈ 1689
        inputs = LaneGroupInput(
            volume=1689,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.vc_ratio == pytest.approx(1.0, rel=0.05)
        assert result.los in [LevelOfService.D, LevelOfService.E, LevelOfService.F]


class TestEngineOversaturated:
    """Tests for oversaturated conditions (v/c > 1)."""

    def test_over_capacity(self):
        """Volume exceeding capacity should be oversaturated."""
        inputs = LaneGroupInput(
            volume=2000,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.vc_ratio > 1.0
        assert result.is_oversaturated is True

    def test_oversaturated_high_delay(self):
        """Oversaturated should have high delay."""
        inputs = LaneGroupInput(
            volume=2500,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.control_delay > 50
        assert result.los in [LevelOfService.E, LevelOfService.F]

    def test_heavily_oversaturated(self):
        """Heavily oversaturated should be LOS F."""
        inputs = LaneGroupInput(
            volume=3000,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.vc_ratio > 1.5
        assert result.is_oversaturated is True
        assert result.los == LevelOfService.F


class TestEngineLaneConfigurations:
    """Tests for different lane configurations."""

    def test_single_lane(self):
        """Single lane approach should work correctly."""
        inputs = LaneGroupInput(
            volume=400,
            num_lanes=1,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.saturation_flow.total_saturation_flow == \
               result.saturation_flow.adjusted_saturation_flow

    def test_multi_lane(self):
        """Multi-lane approach should scale saturation flow."""
        inputs_1 = LaneGroupInput(
            volume=400,
            num_lanes=1,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        inputs_3 = LaneGroupInput(
            volume=1200,
            num_lanes=3,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )

        result_1 = compute_lane_group_results(inputs_1)
        result_3 = compute_lane_group_results(inputs_3)

        # 3 lanes should have 3x saturation flow
        assert result_3.saturation_flow.total_saturation_flow == \
               pytest.approx(3 * result_1.saturation_flow.total_saturation_flow, rel=0.01)

    def test_left_turn_lane(self):
        """Left turn lane should have reduced saturation flow."""
        inputs_through = LaneGroupInput(
            volume=400,
            num_lanes=1,
            movement_type=MovementType.THROUGH,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        inputs_left = LaneGroupInput(
            volume=400,
            num_lanes=1,
            movement_type=MovementType.LEFT,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )

        result_through = compute_lane_group_results(inputs_through)
        result_left = compute_lane_group_results(inputs_left)

        assert result_left.saturation_flow.f_lt < 1.0
        assert result_left.capacity < result_through.capacity


class TestEngineAdjustmentFactors:
    """Tests for adjustment factor effects."""

    def test_heavy_vehicles_reduce_capacity(self):
        """Heavy vehicles should reduce capacity."""
        inputs_no_hv = LaneGroupInput(
            volume=800,
            num_lanes=2,
            heavy_vehicle_pct=0,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        inputs_hv = LaneGroupInput(
            volume=800,
            num_lanes=2,
            heavy_vehicle_pct=20,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )

        result_no_hv = compute_lane_group_results(inputs_no_hv)
        result_hv = compute_lane_group_results(inputs_hv)

        assert result_hv.saturation_flow.f_hv < 1.0
        assert result_hv.capacity < result_no_hv.capacity
        assert result_hv.vc_ratio > result_no_hv.vc_ratio

    def test_cbd_reduces_saturation(self):
        """CBD area should reduce saturation flow."""
        inputs_other = LaneGroupInput(
            volume=800,
            num_lanes=2,
            area_type="other",
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        inputs_cbd = LaneGroupInput(
            volume=800,
            num_lanes=2,
            area_type="cbd",
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )

        result_other = compute_lane_group_results(inputs_other)
        result_cbd = compute_lane_group_results(inputs_cbd)

        assert result_cbd.saturation_flow.f_a == 0.90
        assert result_other.saturation_flow.f_a == 1.00
        assert result_cbd.capacity < result_other.capacity

    def test_grade_effect(self):
        """Uphill grade should reduce capacity."""
        inputs_level = LaneGroupInput(
            volume=800,
            num_lanes=2,
            grade_pct=0,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        inputs_uphill = LaneGroupInput(
            volume=800,
            num_lanes=2,
            grade_pct=6,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )

        result_level = compute_lane_group_results(inputs_level)
        result_uphill = compute_lane_group_results(inputs_uphill)

        assert result_uphill.saturation_flow.f_g < 1.0
        assert result_uphill.capacity < result_level.capacity


class TestEngineSignalTiming:
    """Tests for different signal timing scenarios."""

    def test_short_cycle(self):
        """Short cycle should work correctly."""
        inputs = LaneGroupInput(
            volume=500,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=60,
                effective_green=25
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.capacity > 0
        assert result.control_delay > 0

    def test_long_cycle(self):
        """Long cycle should work correctly."""
        inputs = LaneGroupInput(
            volume=800,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=150,
                effective_green=60
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.capacity > 0
        assert result.control_delay > 0

    def test_actuated_control(self):
        """Actuated control should use different delay factor."""
        inputs = LaneGroupInput(
            volume=800,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40,
                control_type=SignalControlType.ACTUATED_COORDINATED
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.capacity > 0
        # Coordinated should have slightly lower delay


class TestEngineZeroVolume:
    """Tests for zero or very low volume."""

    def test_zero_volume(self):
        """Zero volume should still compute (no demand)."""
        inputs = LaneGroupInput(
            volume=0,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.vc_ratio == 0.0
        assert result.control_delay > 0  # Still has signal delay from red time
        assert result.is_oversaturated is False
        # LOS depends on uniform delay from red time (can be A or B)
        assert result.los in [LevelOfService.A, LevelOfService.B]

    def test_very_low_volume(self):
        """Very low volume should have good LOS."""
        inputs = LaneGroupInput(
            volume=50,
            num_lanes=2,
            signal_timing=SignalTimingInput(
                cycle_length=90,
                effective_green=40
            )
        )
        result = compute_lane_group_results(inputs)

        assert result.vc_ratio < 0.1
        assert result.los in [LevelOfService.A, LevelOfService.B]


class TestEngineValidation:
    """Tests for input validation."""

    def test_negative_volume_rejected(self):
        """Negative volume should be rejected by Pydantic."""
        with pytest.raises(ValueError):
            LaneGroupInput(
                volume=-100,
                num_lanes=2,
                signal_timing=SignalTimingInput(
                    cycle_length=90,
                    effective_green=40
                )
            )

    def test_zero_lanes_rejected(self):
        """Zero lanes should be rejected."""
        with pytest.raises(ValueError):
            LaneGroupInput(
                volume=800,
                num_lanes=0,
                signal_timing=SignalTimingInput(
                    cycle_length=90,
                    effective_green=40
                )
            )

    def test_green_exceeds_cycle_rejected(self):
        """Effective green > cycle should be rejected."""
        with pytest.raises(ValueError):
            LaneGroupInput(
                volume=800,
                num_lanes=2,
                signal_timing=SignalTimingInput(
                    cycle_length=90,
                    effective_green=100
                )
            )

    def test_invalid_area_type_rejected(self):
        """Invalid area type should be rejected."""
        with pytest.raises(ValueError):
            LaneGroupInput(
                volume=800,
                num_lanes=2,
                area_type="downtown",  # Not valid, must be "cbd" or "other"
                signal_timing=SignalTimingInput(
                    cycle_length=90,
                    effective_green=40
                )
            )
