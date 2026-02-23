"""
TIA Report Narrative Generator

Generates professional narrative text from structured analysis results.
Uses only provided data - no hallucinated standards or guidelines.
"""

__version__ = "0.1.0"

from .models import (
    LaneGroupResult,
    IntersectionResult,
    ScenarioResult,
    ScenarioComparison,
    NarrativeSection,
    ReportNarrative,
)
from .service import generate_narrative

__all__ = [
    "__version__",
    "LaneGroupResult",
    "IntersectionResult",
    "ScenarioResult",
    "ScenarioComparison",
    "NarrativeSection",
    "ReportNarrative",
    "generate_narrative",
]
