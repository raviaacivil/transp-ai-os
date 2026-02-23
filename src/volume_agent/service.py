"""
Volume analysis service.

Main entry point for volume data validation and suggestions.
This is an advisory service only - it does not modify data or compute LOS.
"""

from .models import (
    VolumeInput,
    Anomaly,
    AnomalySeverity,
    VolumeAnalysisResult,
)
from .anomalies import detect_all_anomalies
from .suggestions import generate_suggestions


def compute_summary(inputs: VolumeInput) -> dict:
    """
    Compute summary statistics for the volume data.

    Args:
        inputs: Volume input data

    Returns:
        Dictionary of summary statistics
    """
    total_volume = sum(a.movements.total for a in inputs.approaches)

    phf_values = [a.phf for a in inputs.approaches if a.phf is not None]
    avg_phf = sum(phf_values) / len(phf_values) if phf_values else None

    hv_values = [a.heavy_vehicle_pct for a in inputs.approaches
                 if a.heavy_vehicle_pct is not None]
    avg_hv = sum(hv_values) / len(hv_values) if hv_values else None

    return {
        "total_entering_volume": round(total_volume, 0),
        "approaches_analyzed": len(inputs.approaches),
        "average_phf": round(avg_phf, 2) if avg_phf else None,
        "average_heavy_vehicle_pct": round(avg_hv, 1) if avg_hv else None,
        "area_type": inputs.area_type,
        "facility_type": inputs.facility_type,
    }


def analyze_volumes(inputs: VolumeInput) -> VolumeAnalysisResult:
    """
    Analyze volume data for anomalies and generate suggestions.

    This is the main entry point for volume analysis. It:
    1. Detects anomalies in the volume data
    2. Generates structured suggestions for corrections
    3. Computes summary statistics

    This service is advisory only:
    - Does NOT compute LOS
    - Does NOT modify database
    - Does NOT alter input data

    Args:
        inputs: Structured volume input

    Returns:
        VolumeAnalysisResult with anomalies, suggestions, and summary

    Example:
        >>> from volume_agent import analyze_volumes, VolumeInput, ApproachVolume
        >>> inputs = VolumeInput(
        ...     approaches=[
        ...         ApproachVolume(
        ...             name="Northbound",
        ...             movements={"left": 100, "through": 800, "right": 50},
        ...             phf=0.72,  # Low PHF
        ...             heavy_vehicle_pct=3.0
        ...         )
        ...     ],
        ...     area_type="urban"
        ... )
        >>> result = analyze_volumes(inputs)
        >>> print(f"Found {result.anomaly_count} anomalies")
        >>> for s in result.suggestions:
        ...     print(f"  {s.message}")
    """
    # Detect anomalies
    anomalies = detect_all_anomalies(inputs)

    # Count by severity
    warning_count = sum(
        1 for a in anomalies if a.severity == AnomalySeverity.WARNING
    )
    error_count = sum(
        1 for a in anomalies if a.severity == AnomalySeverity.ERROR
    )

    # Generate suggestions
    suggestions = generate_suggestions(inputs, anomalies)

    # Compute summary
    summary = compute_summary(inputs)

    # Determine validity (no errors = valid)
    valid = error_count == 0

    return VolumeAnalysisResult(
        valid=valid,
        anomaly_count=len(anomalies),
        warning_count=warning_count,
        error_count=error_count,
        anomalies=anomalies,
        suggestions=suggestions,
        summary=summary
    )
