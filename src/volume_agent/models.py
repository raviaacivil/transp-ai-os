"""
Pydantic models for volume analysis.

Defines input schemas, anomaly types, and suggestion structures.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# --- Enums ---

class AnomalyType(str, Enum):
    """Types of volume anomalies that can be detected."""

    PHF_OUT_OF_RANGE = "phf_out_of_range"
    PHF_TOO_LOW = "phf_too_low"
    PHF_TOO_HIGH = "phf_too_high"
    HIGH_HEAVY_VEHICLE_PCT = "high_heavy_vehicle_pct"
    VOLUME_IMBALANCE = "volume_imbalance"
    SUSPICIOUS_ROUND_NUMBER = "suspicious_round_number"
    ZERO_VOLUME = "zero_volume"
    VERY_LOW_VOLUME = "very_low_volume"
    UNREALISTIC_HIGH_VOLUME = "unrealistic_high_volume"
    MISSING_DATA = "missing_data"
    PEAK_HOUR_MISMATCH = "peak_hour_mismatch"


class AnomalySeverity(str, Enum):
    """Severity level of detected anomalies."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class SuggestionType(str, Enum):
    """Types of suggestions that can be generated."""

    ADJUST_PHF = "adjust_phf"
    ADJUST_HEAVY_VEHICLE_PCT = "adjust_heavy_vehicle_pct"
    APPLY_GROWTH_FACTOR = "apply_growth_factor"
    BALANCE_VOLUMES = "balance_volumes"
    VERIFY_COUNT = "verify_count"
    USE_DEFAULT_VALUE = "use_default_value"


# --- Input Models ---

class TurningMovement(BaseModel):
    """Volume for a single turning movement."""

    left: float = Field(default=0, ge=0, description="Left turn volume (vph)")
    through: float = Field(default=0, ge=0, description="Through volume (vph)")
    right: float = Field(default=0, ge=0, description="Right turn volume (vph)")

    @property
    def total(self) -> float:
        """Total volume for this approach."""
        return self.left + self.through + self.right


class ApproachVolume(BaseModel):
    """Volume data for a single approach."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Northbound",
                "movements": {"left": 120, "through": 850, "right": 95},
                "phf": 0.92,
                "heavy_vehicle_pct": 3.5,
                "peak_hour_volume": 1065,
                "peak_15_min_volume": 290
            }
        }
    )

    name: str = Field(
        ...,
        description="Approach name (e.g., 'Northbound', 'EB')"
    )
    movements: TurningMovement = Field(
        ...,
        description="Turning movement volumes"
    )
    phf: Optional[float] = Field(
        default=None,
        ge=0,
        le=1.0,
        description="Peak Hour Factor (0.0-1.0)"
    )
    heavy_vehicle_pct: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Percentage of heavy vehicles"
    )
    peak_hour_volume: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total peak hour volume (vph)"
    )
    peak_15_min_volume: Optional[float] = Field(
        default=None,
        ge=0,
        description="Peak 15-minute volume within the peak hour"
    )


class VolumeInput(BaseModel):
    """Input for volume analysis."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "intersection_name": "Main St & 1st Ave",
                "count_date": "2024-03-15",
                "count_period": "PM Peak",
                "approaches": [
                    {
                        "name": "Northbound",
                        "movements": {"left": 120, "through": 850, "right": 95},
                        "phf": 0.92,
                        "heavy_vehicle_pct": 3.5
                    },
                    {
                        "name": "Southbound",
                        "movements": {"left": 85, "through": 920, "right": 110},
                        "phf": 0.88,
                        "heavy_vehicle_pct": 4.0
                    }
                ],
                "area_type": "urban",
                "facility_type": "arterial"
            }
        }
    )

    intersection_name: Optional[str] = Field(
        default=None,
        description="Name of the intersection"
    )
    count_date: Optional[str] = Field(
        default=None,
        description="Date of traffic count (YYYY-MM-DD)"
    )
    count_period: Optional[str] = Field(
        default=None,
        description="Count period (e.g., 'AM Peak', 'PM Peak')"
    )
    approaches: list[ApproachVolume] = Field(
        ...,
        min_length=1,
        description="List of approach volumes"
    )
    area_type: str = Field(
        default="urban",
        pattern="^(urban|suburban|rural|cbd)$",
        description="Area type for context"
    )
    facility_type: str = Field(
        default="arterial",
        pattern="^(arterial|collector|local|freeway)$",
        description="Facility type for context"
    )
    base_year: Optional[int] = Field(
        default=None,
        ge=1990,
        le=2100,
        description="Base year of counts"
    )
    analysis_year: Optional[int] = Field(
        default=None,
        ge=1990,
        le=2100,
        description="Target analysis year (for growth)"
    )
    annual_growth_rate: Optional[float] = Field(
        default=None,
        ge=-5,
        le=10,
        description="Annual growth rate in percent"
    )


# --- Output Models ---

class Anomaly(BaseModel):
    """A detected anomaly in the volume data."""

    type: AnomalyType = Field(description="Type of anomaly")
    severity: AnomalySeverity = Field(description="Severity level")
    location: str = Field(description="Where the anomaly was found")
    message: str = Field(description="Human-readable description")
    current_value: Optional[float] = Field(
        default=None,
        description="Current value that triggered the anomaly"
    )
    expected_range: Optional[str] = Field(
        default=None,
        description="Expected range or value"
    )


class Suggestion(BaseModel):
    """A suggested correction or adjustment."""

    type: SuggestionType = Field(description="Type of suggestion")
    location: str = Field(description="Where to apply the suggestion")
    message: str = Field(description="Human-readable suggestion")
    current_value: Optional[float] = Field(
        default=None,
        description="Current value"
    )
    suggested_value: Optional[float] = Field(
        default=None,
        description="Suggested new value"
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in this suggestion (0-1)"
    )
    rationale: str = Field(description="Why this suggestion is made")


class VolumeAnalysisResult(BaseModel):
    """Complete result of volume analysis."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "valid": False,
                "anomaly_count": 2,
                "anomalies": [
                    {
                        "type": "phf_too_low",
                        "severity": "warning",
                        "location": "Southbound",
                        "message": "PHF of 0.72 is below typical minimum of 0.85",
                        "current_value": 0.72,
                        "expected_range": "0.85-0.95"
                    }
                ],
                "suggestions": [
                    {
                        "type": "adjust_phf",
                        "location": "Southbound",
                        "message": "Consider adjusting PHF to 0.88",
                        "current_value": 0.72,
                        "suggested_value": 0.88,
                        "confidence": 0.75,
                        "rationale": "PHF below 0.85 is unusual for urban arterials"
                    }
                ],
                "summary": {
                    "total_entering_volume": 4500,
                    "approaches_analyzed": 4,
                    "average_phf": 0.89
                }
            }
        }
    )

    valid: bool = Field(
        description="Whether data passed all critical checks"
    )
    anomaly_count: int = Field(
        description="Total number of anomalies detected"
    )
    warning_count: int = Field(
        default=0,
        description="Number of warning-level anomalies"
    )
    error_count: int = Field(
        default=0,
        description="Number of error-level anomalies"
    )
    anomalies: list[Anomaly] = Field(
        default_factory=list,
        description="List of detected anomalies"
    )
    suggestions: list[Suggestion] = Field(
        default_factory=list,
        description="List of suggested corrections"
    )
    summary: dict = Field(
        default_factory=dict,
        description="Summary statistics"
    )
