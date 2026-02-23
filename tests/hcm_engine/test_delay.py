"""
Tests for delay calculations.

Tests verify HCM 6th Edition control delay equations.
"""

import pytest
from src.hcm_engine.delay import (
    compute_uniform_delay,
    compute_incremental_delay,
    compute_control_delay,
    get_incremental_delay_factor,
)
from src.hcm_engine.models import SignalControlType


class TestUniformDelay:
    """Tests for uniform delay (d1) calculation."""

    def test_undersaturated_typical(self):
        """Test typical undersaturated condition."""
        d1 = compute_uniform_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.5
        )
        # Should be positive and reasonable
        assert d1 > 0
        assert d1 < 30  # Reasonable bound for undersaturated

    def test_low_vc_ratio(self):
        """Test with very low v/c ratio."""
        d1 = compute_uniform_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.1
        )
        # Low v/c should have lower delay
        assert d1 > 0
        assert d1 < 20

    def test_at_capacity(self):
        """Test at capacity (v/c = 1)."""
        d1 = compute_uniform_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=1.0
        )
        # At capacity, delay increases
        assert d1 > 0

    def test_oversaturated(self):
        """Test oversaturated (v/c > 1)."""
        d1_at_capacity = compute_uniform_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=1.0
        )
        d1_oversaturated = compute_uniform_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=1.5
        )
        # Uniform delay uses min(1, X), so should be same
        assert d1_at_capacity == d1_oversaturated

    def test_high_green_ratio(self):
        """Test with high g/C ratio (should reduce delay)."""
        d1_low_gc = compute_uniform_delay(
            effective_green=30,
            cycle_length=90,
            vc_ratio=0.5
        )
        d1_high_gc = compute_uniform_delay(
            effective_green=60,
            cycle_length=90,
            vc_ratio=0.5
        )
        assert d1_high_gc < d1_low_gc

    def test_short_cycle(self):
        """Test with short cycle length."""
        d1 = compute_uniform_delay(
            effective_green=20,
            cycle_length=60,
            vc_ratio=0.5
        )
        assert d1 > 0

    def test_long_cycle(self):
        """Test with long cycle length."""
        d1_short = compute_uniform_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.5
        )
        d1_long = compute_uniform_delay(
            effective_green=60,
            cycle_length=150,
            vc_ratio=0.5
        )
        # Longer cycle (same g/C) should have higher delay
        assert d1_long > d1_short

    def test_invalid_cycle_length(self):
        """Zero cycle length should raise error."""
        with pytest.raises(ValueError):
            compute_uniform_delay(
                effective_green=40,
                cycle_length=0,
                vc_ratio=0.5
            )


class TestIncrementalDelay:
    """Tests for incremental delay (d2) calculation."""

    def test_undersaturated(self):
        """Test undersaturated condition (v/c < 1)."""
        d2 = compute_incremental_delay(
            vc_ratio=0.5,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        # Undersaturated should have minimal incremental delay
        assert d2 >= 0
        assert d2 < 10

    def test_at_capacity(self):
        """Test at capacity (v/c = 1)."""
        d2 = compute_incremental_delay(
            vc_ratio=1.0,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        # At capacity, incremental delay increases
        assert d2 > 0

    def test_oversaturated(self):
        """Test oversaturated condition (v/c > 1)."""
        d2_at_cap = compute_incremental_delay(
            vc_ratio=1.0,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        d2_over = compute_incremental_delay(
            vc_ratio=1.2,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        # Oversaturated should have higher delay
        assert d2_over > d2_at_cap

    def test_heavily_oversaturated(self):
        """Test heavily oversaturated (v/c >> 1)."""
        d2 = compute_incremental_delay(
            vc_ratio=1.5,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        # Should have significant delay
        assert d2 > 50

    def test_low_capacity(self):
        """Test with low capacity (minor street)."""
        d2 = compute_incremental_delay(
            vc_ratio=0.8,
            capacity=300,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        assert d2 > 0

    def test_analysis_period_effect(self):
        """Longer analysis period increases delay for oversaturated."""
        d2_15min = compute_incremental_delay(
            vc_ratio=1.2,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        d2_60min = compute_incremental_delay(
            vc_ratio=1.2,
            capacity=1600,
            analysis_period_hours=1.0,
            control_type=SignalControlType.PRETIMED
        )
        # Longer period with overflow means more delay
        assert d2_60min > d2_15min

    def test_invalid_capacity(self):
        """Zero capacity should raise error."""
        with pytest.raises(ValueError):
            compute_incremental_delay(
                vc_ratio=0.5,
                capacity=0,
                analysis_period_hours=0.25,
                control_type=SignalControlType.PRETIMED
            )

    def test_invalid_analysis_period(self):
        """Zero analysis period should raise error."""
        with pytest.raises(ValueError):
            compute_incremental_delay(
                vc_ratio=0.5,
                capacity=1600,
                analysis_period_hours=0,
                control_type=SignalControlType.PRETIMED
            )


class TestIncrementalDelayFactor:
    """Tests for incremental delay factor (k)."""

    def test_pretimed(self):
        """Pretimed should have k = 0.50."""
        k = get_incremental_delay_factor(SignalControlType.PRETIMED)
        assert k == 0.50

    def test_actuated_uncoordinated(self):
        """Actuated uncoordinated should have k = 0.50."""
        k = get_incremental_delay_factor(SignalControlType.ACTUATED_UNCOORDINATED)
        assert k == 0.50

    def test_actuated_coordinated(self):
        """Actuated coordinated should have k = 0.45."""
        k = get_incremental_delay_factor(SignalControlType.ACTUATED_COORDINATED)
        assert k == 0.45


class TestControlDelay:
    """Tests for total control delay calculation."""

    def test_returns_three_values(self):
        """Should return d1, d2, and total delay."""
        result = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.5,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        assert len(result) == 3
        d1, d2, total = result
        assert total == pytest.approx(d1 + d2, rel=0.01)

    def test_total_equals_components(self):
        """Total delay should equal d1 + d2."""
        d1, d2, total = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.8,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        assert total == pytest.approx(d1 + d2, rel=0.01)

    def test_undersaturated_reasonable_delay(self):
        """Undersaturated should have reasonable total delay."""
        _, _, total = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.5,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        # Typical undersaturated delay should be < 30 sec
        assert total > 0
        assert total < 30

    def test_at_capacity_delay(self):
        """At capacity should have higher delay."""
        _, _, total_under = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.5,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        _, _, total_at = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=1.0,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        assert total_at > total_under

    def test_oversaturated_delay(self):
        """Oversaturated should have high delay."""
        _, _, total = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=1.3,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        # Oversaturated should have significant delay
        assert total > 50


class TestDelayEdgeCases:
    """Edge case tests for delay calculations."""

    def test_zero_vc_ratio(self):
        """Zero v/c should have minimal delay."""
        d1, d2, total = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.0,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        # Should still have some uniform delay (red time)
        assert d1 > 0
        assert d2 >= 0
        assert total > 0

    def test_very_high_vc_ratio(self):
        """Very high v/c should have very high delay."""
        _, _, total = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=2.0,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED
        )
        # Severely oversaturated should have very high delay
        assert total > 100

    def test_upstream_filtering_effect(self):
        """Upstream filtering should reduce delay."""
        _, _, total_isolated = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.8,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED,
            upstream_filtering_factor=1.0
        )
        _, _, total_coordinated = compute_control_delay(
            effective_green=40,
            cycle_length=90,
            vc_ratio=0.8,
            capacity=1600,
            analysis_period_hours=0.25,
            control_type=SignalControlType.PRETIMED,
            upstream_filtering_factor=0.7
        )
        # Lower I factor should reduce incremental delay
        assert total_coordinated < total_isolated
