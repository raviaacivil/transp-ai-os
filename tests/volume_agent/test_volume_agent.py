"""Tests for volume analysis agent."""

import pytest
from src.volume_agent import (
    analyze_volumes,
    VolumeInput,
    ApproachVolume,
    AnomalyType,
    AnomalySeverity,
    SuggestionType,
)
from src.volume_agent.models import TurningMovement


class TestVolumeInput:
    """Tests for input model validation."""

    def test_valid_input(self):
        """Valid input should be accepted."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="Northbound",
                    movements=TurningMovement(left=100, through=800, right=50),
                    phf=0.92,
                    heavy_vehicle_pct=3.0
                )
            ]
        )
        assert len(inputs.approaches) == 1

    def test_movement_total(self):
        """Movement total should sum correctly."""
        movement = TurningMovement(left=100, through=800, right=50)
        assert movement.total == 950

    def test_default_area_type(self):
        """Default area type should be urban."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(left=100, through=800, right=50)
                )
            ]
        )
        assert inputs.area_type == "urban"


class TestPHFAnomalyDetection:
    """Tests for PHF anomaly detection."""

    def test_valid_phf_no_anomaly(self):
        """Valid PHF should not trigger anomaly."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.92
                )
            ],
            area_type="urban"
        )
        result = analyze_volumes(inputs)
        phf_anomalies = [a for a in result.anomalies
                        if a.type in (AnomalyType.PHF_TOO_LOW,
                                     AnomalyType.PHF_OUT_OF_RANGE)]
        assert len(phf_anomalies) == 0

    def test_phf_below_minimum(self):
        """PHF below 0.70 should trigger error."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.65
                )
            ]
        )
        result = analyze_volumes(inputs)
        assert result.error_count > 0
        assert any(a.type == AnomalyType.PHF_OUT_OF_RANGE for a in result.anomalies)

    def test_phf_too_low_for_urban(self):
        """PHF below 0.85 should trigger warning for urban."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.78
                )
            ],
            area_type="urban"
        )
        result = analyze_volumes(inputs)
        assert any(a.type == AnomalyType.PHF_TOO_LOW for a in result.anomalies)

    def test_phf_missing(self):
        """Missing PHF should trigger info."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800)
                )
            ]
        )
        result = analyze_volumes(inputs)
        assert any(a.type == AnomalyType.MISSING_DATA for a in result.anomalies)


class TestHeavyVehicleAnomalyDetection:
    """Tests for heavy vehicle anomaly detection."""

    def test_normal_hv_no_anomaly(self):
        """Normal HV% should not trigger anomaly."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    heavy_vehicle_pct=4.0
                )
            ],
            area_type="urban"
        )
        result = analyze_volumes(inputs)
        hv_anomalies = [a for a in result.anomalies
                       if a.type == AnomalyType.HIGH_HEAVY_VEHICLE_PCT]
        assert len(hv_anomalies) == 0

    def test_high_hv_urban(self):
        """High HV% in urban should trigger anomaly."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    heavy_vehicle_pct=18.0
                )
            ],
            area_type="urban"
        )
        result = analyze_volumes(inputs)
        assert any(a.type == AnomalyType.HIGH_HEAVY_VEHICLE_PCT
                  for a in result.anomalies)

    def test_high_hv_rural_ok(self):
        """Higher HV% acceptable in rural areas."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    heavy_vehicle_pct=15.0
                )
            ],
            area_type="rural"
        )
        result = analyze_volumes(inputs)
        hv_anomalies = [a for a in result.anomalies
                       if a.type == AnomalyType.HIGH_HEAVY_VEHICLE_PCT
                       and a.severity == AnomalySeverity.WARNING]
        assert len(hv_anomalies) == 0


class TestVolumeAnomalyDetection:
    """Tests for volume anomaly detection."""

    def test_zero_volume(self):
        """Zero volume should trigger warning."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(left=0, through=0, right=0)
                )
            ]
        )
        result = analyze_volumes(inputs)
        assert any(a.type == AnomalyType.ZERO_VOLUME for a in result.anomalies)

    def test_very_low_volume(self):
        """Very low volume should trigger info."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=25)
                )
            ],
            area_type="urban"
        )
        result = analyze_volumes(inputs)
        assert any(a.type == AnomalyType.VERY_LOW_VOLUME for a in result.anomalies)

    def test_suspicious_round_number(self):
        """Round numbers should trigger info."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=500)
                )
            ]
        )
        result = analyze_volumes(inputs)
        assert any(a.type == AnomalyType.SUSPICIOUS_ROUND_NUMBER
                  for a in result.anomalies)

    def test_unrealistic_high_volume(self):
        """Very high volume should trigger warning."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=5000)
                )
            ]
        )
        result = analyze_volumes(inputs)
        assert any(a.type == AnomalyType.UNREALISTIC_HIGH_VOLUME
                  for a in result.anomalies)


class TestVolumeImbalance:
    """Tests for volume imbalance detection."""

    def test_balanced_volumes(self):
        """Balanced opposing volumes should not trigger anomaly."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="Northbound",
                    movements=TurningMovement(through=800)
                ),
                ApproachVolume(
                    name="Southbound",
                    movements=TurningMovement(through=850)
                )
            ]
        )
        result = analyze_volumes(inputs)
        imbalance = [a for a in result.anomalies
                    if a.type == AnomalyType.VOLUME_IMBALANCE]
        assert len(imbalance) == 0

    def test_imbalanced_volumes(self):
        """Significantly imbalanced volumes should trigger info."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="Northbound",
                    movements=TurningMovement(through=800)
                ),
                ApproachVolume(
                    name="Southbound",
                    movements=TurningMovement(through=200)
                )
            ]
        )
        result = analyze_volumes(inputs)
        assert any(a.type == AnomalyType.VOLUME_IMBALANCE for a in result.anomalies)


class TestPHFSuggestions:
    """Tests for PHF suggestion generation."""

    def test_suggest_default_phf(self):
        """Should suggest default PHF when missing."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800)
                )
            ],
            area_type="urban"
        )
        result = analyze_volumes(inputs)
        phf_suggestions = [s for s in result.suggestions
                         if s.type == SuggestionType.USE_DEFAULT_VALUE]
        assert len(phf_suggestions) > 0
        assert phf_suggestions[0].suggested_value == 0.90

    def test_suggest_phf_correction(self):
        """Should suggest PHF correction when too low."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.75
                )
            ],
            area_type="urban"
        )
        result = analyze_volumes(inputs)
        phf_suggestions = [s for s in result.suggestions
                         if s.type == SuggestionType.ADJUST_PHF]
        assert len(phf_suggestions) > 0

    def test_calculate_phf_from_volumes(self):
        """Should calculate PHF from peak volumes when available."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    peak_hour_volume=1000,
                    peak_15_min_volume=280
                )
            ]
        )
        result = analyze_volumes(inputs)
        phf_suggestions = [s for s in result.suggestions
                         if s.type == SuggestionType.ADJUST_PHF]
        assert len(phf_suggestions) > 0
        # PHF = 1000 / (4 * 280) = 0.893
        assert phf_suggestions[0].suggested_value == pytest.approx(0.89, rel=0.02)


class TestGrowthSuggestions:
    """Tests for growth factor suggestions."""

    def test_suggest_growth_factor(self):
        """Should suggest growth factor when years differ."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.92
                )
            ],
            base_year=2020,
            analysis_year=2030,
            area_type="suburban"
        )
        result = analyze_volumes(inputs)
        growth_suggestions = [s for s in result.suggestions
                             if s.type == SuggestionType.APPLY_GROWTH_FACTOR]
        assert len(growth_suggestions) == 1
        # 10 years at 2% = 1.219
        assert growth_suggestions[0].suggested_value == pytest.approx(1.219, rel=0.01)

    def test_use_provided_growth_rate(self):
        """Should use provided growth rate."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.92
                )
            ],
            base_year=2020,
            analysis_year=2025,
            annual_growth_rate=3.0
        )
        result = analyze_volumes(inputs)
        growth_suggestions = [s for s in result.suggestions
                             if s.type == SuggestionType.APPLY_GROWTH_FACTOR]
        assert len(growth_suggestions) == 1
        # 5 years at 3% = 1.159
        assert growth_suggestions[0].suggested_value == pytest.approx(1.159, rel=0.01)

    def test_no_growth_same_year(self):
        """Should not suggest growth when years are same."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.92
                )
            ],
            base_year=2024,
            analysis_year=2024
        )
        result = analyze_volumes(inputs)
        growth_suggestions = [s for s in result.suggestions
                             if s.type == SuggestionType.APPLY_GROWTH_FACTOR]
        assert len(growth_suggestions) == 0


class TestAnalysisResult:
    """Tests for analysis result structure."""

    def test_result_structure(self):
        """Result should have all required fields."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.92
                )
            ]
        )
        result = analyze_volumes(inputs)

        assert hasattr(result, "valid")
        assert hasattr(result, "anomaly_count")
        assert hasattr(result, "anomalies")
        assert hasattr(result, "suggestions")
        assert hasattr(result, "summary")

    def test_summary_statistics(self):
        """Summary should include key statistics."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(left=100, through=800, right=50),
                    phf=0.92,
                    heavy_vehicle_pct=3.0
                ),
                ApproachVolume(
                    name="SB",
                    movements=TurningMovement(left=80, through=750, right=70),
                    phf=0.88,
                    heavy_vehicle_pct=4.0
                )
            ]
        )
        result = analyze_volumes(inputs)

        assert result.summary["total_entering_volume"] == 1850
        assert result.summary["approaches_analyzed"] == 2
        assert result.summary["average_phf"] == 0.90
        assert result.summary["average_heavy_vehicle_pct"] == 3.5

    def test_valid_with_no_errors(self):
        """Valid should be True when no errors."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.92,
                    heavy_vehicle_pct=3.0
                )
            ]
        )
        result = analyze_volumes(inputs)
        assert result.valid is True
        assert result.error_count == 0

    def test_invalid_with_errors(self):
        """Valid should be False when errors exist."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.50  # Invalid PHF
                )
            ]
        )
        result = analyze_volumes(inputs)
        assert result.valid is False
        assert result.error_count > 0


class TestMultipleApproaches:
    """Tests with multiple approaches."""

    def test_four_approach_intersection(self):
        """Should handle 4-approach intersection."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="Northbound",
                    movements=TurningMovement(left=100, through=800, right=50),
                    phf=0.92
                ),
                ApproachVolume(
                    name="Southbound",
                    movements=TurningMovement(left=80, through=750, right=70),
                    phf=0.88
                ),
                ApproachVolume(
                    name="Eastbound",
                    movements=TurningMovement(left=60, through=500, right=40),
                    phf=0.90
                ),
                ApproachVolume(
                    name="Westbound",
                    movements=TurningMovement(left=70, through=480, right=50),
                    phf=0.89
                )
            ]
        )
        result = analyze_volumes(inputs)

        assert result.summary["approaches_analyzed"] == 4
        assert result.summary["total_entering_volume"] == 3050

    def test_anomalies_per_approach(self):
        """Should detect anomalies for each approach."""
        inputs = VolumeInput(
            approaches=[
                ApproachVolume(
                    name="NB",
                    movements=TurningMovement(through=800),
                    phf=0.75  # Low
                ),
                ApproachVolume(
                    name="SB",
                    movements=TurningMovement(through=800),
                    phf=0.65  # Invalid
                )
            ],
            area_type="urban"
        )
        result = analyze_volumes(inputs)

        nb_anomalies = [a for a in result.anomalies if a.location == "NB"]
        sb_anomalies = [a for a in result.anomalies if a.location == "SB"]

        assert len(nb_anomalies) > 0
        assert len(sb_anomalies) > 0
