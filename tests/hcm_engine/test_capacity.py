"""
Tests for capacity calculations.

Tests verify HCM 6th Edition capacity and v/c ratio equations.
"""

import pytest
from src.hcm_engine.capacity import compute_capacity, compute_vc_ratio


class TestComputeCapacity:
    """Tests for capacity calculation."""

    def test_basic_capacity(self):
        """Test basic capacity calculation c = s * g/C."""
        # 2 lanes at 1900 pc/h/ln = 3800 vph saturation
        # 40 sec green, 90 sec cycle => g/C = 0.444
        capacity = compute_capacity(
            saturation_flow=3800,
            effective_green=40,
            cycle_length=90
        )
        expected = 3800 * (40 / 90)  # 1688.9
        assert capacity == pytest.approx(expected, rel=0.01)

    def test_high_green_ratio(self):
        """Test with high g/C ratio (major street)."""
        capacity = compute_capacity(
            saturation_flow=3800,
            effective_green=60,
            cycle_length=90
        )
        expected = 3800 * (60 / 90)  # 2533.3
        assert capacity == pytest.approx(expected, rel=0.01)

    def test_low_green_ratio(self):
        """Test with low g/C ratio (minor street)."""
        capacity = compute_capacity(
            saturation_flow=1900,
            effective_green=20,
            cycle_length=120
        )
        expected = 1900 * (20 / 120)  # 316.7
        assert capacity == pytest.approx(expected, rel=0.01)

    def test_full_green(self):
        """Test when effective green equals cycle length."""
        capacity = compute_capacity(
            saturation_flow=1900,
            effective_green=60,
            cycle_length=60
        )
        # Full green means capacity equals saturation flow
        assert capacity == pytest.approx(1900, rel=0.01)

    def test_zero_saturation_flow(self):
        """Zero saturation flow means zero capacity."""
        capacity = compute_capacity(
            saturation_flow=0,
            effective_green=40,
            cycle_length=90
        )
        assert capacity == 0.0

    def test_invalid_cycle_length(self):
        """Zero cycle length should raise error."""
        with pytest.raises(ValueError, match="cycle_length must be positive"):
            compute_capacity(
                saturation_flow=1900,
                effective_green=40,
                cycle_length=0
            )

    def test_invalid_effective_green(self):
        """Negative effective green should raise error."""
        with pytest.raises(ValueError, match="effective_green cannot be negative"):
            compute_capacity(
                saturation_flow=1900,
                effective_green=-10,
                cycle_length=90
            )

    def test_green_exceeds_cycle(self):
        """Effective green exceeding cycle should raise error."""
        with pytest.raises(ValueError, match="effective_green cannot exceed"):
            compute_capacity(
                saturation_flow=1900,
                effective_green=100,
                cycle_length=90
            )

    def test_negative_saturation_flow(self):
        """Negative saturation flow should raise error."""
        with pytest.raises(ValueError, match="saturation_flow cannot be negative"):
            compute_capacity(
                saturation_flow=-1900,
                effective_green=40,
                cycle_length=90
            )


class TestComputeVCRatio:
    """Tests for v/c ratio calculation."""

    def test_undersaturated(self):
        """Test undersaturated condition (v/c < 1)."""
        vc = compute_vc_ratio(volume=800, capacity=1600)
        assert vc == 0.5
        assert vc < 1.0

    def test_at_capacity(self):
        """Test at-capacity condition (v/c = 1)."""
        vc = compute_vc_ratio(volume=1600, capacity=1600)
        assert vc == 1.0

    def test_oversaturated(self):
        """Test oversaturated condition (v/c > 1)."""
        vc = compute_vc_ratio(volume=2000, capacity=1600)
        assert vc == 1.25
        assert vc > 1.0

    def test_heavily_oversaturated(self):
        """Test heavily oversaturated (v/c >> 1)."""
        vc = compute_vc_ratio(volume=3200, capacity=1600)
        assert vc == 2.0

    def test_zero_volume(self):
        """Zero volume should give zero v/c."""
        vc = compute_vc_ratio(volume=0, capacity=1600)
        assert vc == 0.0

    def test_zero_capacity_raises(self):
        """Zero capacity should raise error."""
        with pytest.raises(ValueError, match="capacity must be positive"):
            compute_vc_ratio(volume=800, capacity=0)

    def test_negative_capacity_raises(self):
        """Negative capacity should raise error."""
        with pytest.raises(ValueError, match="capacity must be positive"):
            compute_vc_ratio(volume=800, capacity=-1600)

    def test_negative_volume_raises(self):
        """Negative volume should raise error."""
        with pytest.raises(ValueError, match="volume cannot be negative"):
            compute_vc_ratio(volume=-800, capacity=1600)

    def test_precision(self):
        """Test that v/c ratio has appropriate precision."""
        vc = compute_vc_ratio(volume=1000, capacity=1234)
        # Should have 4 decimal places
        assert vc == round(1000 / 1234, 4)


class TestVCRatioEdgeCases:
    """Edge case tests for v/c ratio."""

    def test_near_capacity(self):
        """Test v/c very close to 1.0."""
        vc = compute_vc_ratio(volume=999, capacity=1000)
        assert vc == 0.999

    def test_slightly_over_capacity(self):
        """Test v/c slightly over 1.0."""
        vc = compute_vc_ratio(volume=1001, capacity=1000)
        assert vc == 1.001

    def test_very_low_volume(self):
        """Test very low volume."""
        vc = compute_vc_ratio(volume=1, capacity=1000)
        assert vc == 0.001

    def test_very_high_vc(self):
        """Test very high v/c ratio (severe oversaturation)."""
        vc = compute_vc_ratio(volume=5000, capacity=1000)
        assert vc == 5.0
