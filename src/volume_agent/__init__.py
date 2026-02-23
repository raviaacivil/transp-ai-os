"""
Volume Cleanup Agent

AI-assisted volume data validation and suggestion service.
Flags anomalies and provides structured recommendations.

This agent is advisory only - it does not modify data or compute LOS.
"""

__version__ = "0.1.0"

from .models import (
    VolumeInput,
    ApproachVolume,
    AnomalyType,
    AnomalySeverity,
    Anomaly,
    Suggestion,
    SuggestionType,
    VolumeAnalysisResult,
)
from .service import analyze_volumes

__all__ = [
    "__version__",
    "VolumeInput",
    "ApproachVolume",
    "AnomalyType",
    "AnomalySeverity",
    "Anomaly",
    "Suggestion",
    "SuggestionType",
    "VolumeAnalysisResult",
    "analyze_volumes",
]
