"""
Tests for Level of Service classification.

Tests verify HCM 6th Edition LOS thresholds.
"""

import pytest
from src.hcm_engine.los import (
    classify_los,
    get_los_description,
    LOS_THRESHOLDS,
)
from src.hcm_engine.models import LevelOfService


class TestClassifyLOS:
    """Tests for LOS classification."""

    def test_los_a(self):
        """Test LOS A classification (delay <= 10 sec)."""
        assert classify_los(0) == LevelOfService.A
        assert classify_los(5) == LevelOfService.A
        assert classify_los(10) == LevelOfService.A

    def test_los_b(self):
        """Test LOS B classification (10 < delay <= 20 sec)."""
        assert classify_los(10.1) == LevelOfService.B
        assert classify_los(15) == LevelOfService.B
        assert classify_los(20) == LevelOfService.B

    def test_los_c(self):
        """Test LOS C classification (20 < delay <= 35 sec)."""
        assert classify_los(20.1) == LevelOfService.C
        assert classify_los(25) == LevelOfService.C
        assert classify_los(35) == LevelOfService.C

    def test_los_d(self):
        """Test LOS D classification (35 < delay <= 55 sec)."""
        assert classify_los(35.1) == LevelOfService.D
        assert classify_los(45) == LevelOfService.D
        assert classify_los(55) == LevelOfService.D

    def test_los_e(self):
        """Test LOS E classification (55 < delay <= 80 sec)."""
        assert classify_los(55.1) == LevelOfService.E
        assert classify_los(70) == LevelOfService.E
        assert classify_los(80) == LevelOfService.E

    def test_los_f(self):
        """Test LOS F classification (delay > 80 sec)."""
        assert classify_los(80.1) == LevelOfService.F
        assert classify_los(100) == LevelOfService.F
        assert classify_los(200) == LevelOfService.F
        assert classify_los(1000) == LevelOfService.F

    def test_negative_delay_raises(self):
        """Negative delay should raise error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            classify_los(-1)

    def test_boundary_values(self):
        """Test exact boundary values."""
        assert classify_los(10.0) == LevelOfService.A
        assert classify_los(10.01) == LevelOfService.B
        assert classify_los(20.0) == LevelOfService.B
        assert classify_los(20.01) == LevelOfService.C
        assert classify_los(35.0) == LevelOfService.C
        assert classify_los(35.01) == LevelOfService.D
        assert classify_los(55.0) == LevelOfService.D
        assert classify_los(55.01) == LevelOfService.E
        assert classify_los(80.0) == LevelOfService.E
        assert classify_los(80.01) == LevelOfService.F


class TestLOSThresholds:
    """Tests for LOS threshold constants."""

    def test_thresholds_exist(self):
        """All LOS grades should have thresholds (except F)."""
        assert LevelOfService.A in LOS_THRESHOLDS
        assert LevelOfService.B in LOS_THRESHOLDS
        assert LevelOfService.C in LOS_THRESHOLDS
        assert LevelOfService.D in LOS_THRESHOLDS
        assert LevelOfService.E in LOS_THRESHOLDS

    def test_thresholds_increasing(self):
        """Thresholds should be strictly increasing."""
        assert LOS_THRESHOLDS[LevelOfService.A] < LOS_THRESHOLDS[LevelOfService.B]
        assert LOS_THRESHOLDS[LevelOfService.B] < LOS_THRESHOLDS[LevelOfService.C]
        assert LOS_THRESHOLDS[LevelOfService.C] < LOS_THRESHOLDS[LevelOfService.D]
        assert LOS_THRESHOLDS[LevelOfService.D] < LOS_THRESHOLDS[LevelOfService.E]

    def test_threshold_values(self):
        """Verify HCM 6th Edition threshold values."""
        assert LOS_THRESHOLDS[LevelOfService.A] == 10.0
        assert LOS_THRESHOLDS[LevelOfService.B] == 20.0
        assert LOS_THRESHOLDS[LevelOfService.C] == 35.0
        assert LOS_THRESHOLDS[LevelOfService.D] == 55.0
        assert LOS_THRESHOLDS[LevelOfService.E] == 80.0


class TestLOSDescription:
    """Tests for LOS descriptions."""

    def test_all_los_have_descriptions(self):
        """All LOS grades should have descriptions."""
        for los in LevelOfService:
            description = get_los_description(los)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_los_a_description(self):
        """LOS A should indicate free flow."""
        desc = get_los_description(LevelOfService.A)
        assert "free" in desc.lower() or "flow" in desc.lower()

    def test_los_f_description(self):
        """LOS F should indicate oversaturation."""
        desc = get_los_description(LevelOfService.F)
        assert "oversaturated" in desc.lower() or "forced" in desc.lower()


class TestLOSEnum:
    """Tests for LevelOfService enum."""

    def test_enum_values(self):
        """Enum values should be single letters."""
        assert LevelOfService.A.value == "A"
        assert LevelOfService.B.value == "B"
        assert LevelOfService.C.value == "C"
        assert LevelOfService.D.value == "D"
        assert LevelOfService.E.value == "E"
        assert LevelOfService.F.value == "F"

    def test_enum_string_conversion(self):
        """Enum should convert to string properly."""
        assert str(LevelOfService.A) == "LevelOfService.A"
        assert LevelOfService.A.value == "A"

    def test_enum_comparison(self):
        """Enums should be comparable."""
        assert LevelOfService.A == LevelOfService.A
        assert LevelOfService.A != LevelOfService.B
