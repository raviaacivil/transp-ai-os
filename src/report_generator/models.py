"""
Pydantic models for report narrative generation.

Input models accept analysis results.
Output models provide structured narrative sections.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class LOS(str, Enum):
    """Level of Service grades."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class AnalysisPeriod(str, Enum):
    """Standard analysis periods."""
    AM_PEAK = "AM Peak"
    PM_PEAK = "PM Peak"
    WEEKDAY = "Weekday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"


class ScenarioType(str, Enum):
    """Standard scenario types for TIA."""
    EXISTING = "Existing"
    BACKGROUND = "Background"
    BUILD = "Build"
    CUMULATIVE = "Cumulative"
    MITIGATION = "Mitigation"


# --- Input Models ---

class LaneGroupResult(BaseModel):
    """Results for a single lane group."""

    name: str = Field(description="Lane group name (e.g., 'NBL', 'EBT')")
    movement: str = Field(description="Movement description")
    volume: float = Field(ge=0, description="Volume in vph")
    capacity: float = Field(gt=0, description="Capacity in vph")
    vc_ratio: float = Field(ge=0, description="Volume-to-capacity ratio")
    delay: float = Field(ge=0, description="Control delay in seconds")
    los: LOS = Field(description="Level of Service")
    queue_50th: Optional[float] = Field(
        default=None,
        ge=0,
        description="50th percentile queue in feet"
    )
    queue_95th: Optional[float] = Field(
        default=None,
        ge=0,
        description="95th percentile queue in feet"
    )


class IntersectionResult(BaseModel):
    """Complete results for an intersection."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Main St & 1st Ave",
                "control_type": "Signalized",
                "analysis_period": "PM Peak",
                "overall_los": "C",
                "overall_delay": 28.5,
                "worst_approach_los": "D",
                "worst_approach_name": "Eastbound",
                "lane_groups": []
            }
        }
    )

    name: str = Field(description="Intersection name")
    control_type: str = Field(
        default="Signalized",
        description="Control type (Signalized, TWSC, AWSC, Roundabout)"
    )
    analysis_period: AnalysisPeriod = Field(description="Analysis period")
    overall_los: LOS = Field(description="Overall intersection LOS")
    overall_delay: float = Field(ge=0, description="Overall delay in seconds")
    overall_vc: Optional[float] = Field(
        default=None,
        ge=0,
        description="Critical v/c ratio (if applicable)"
    )
    worst_approach_los: Optional[LOS] = Field(
        default=None,
        description="Worst approach LOS"
    )
    worst_approach_name: Optional[str] = Field(
        default=None,
        description="Name of worst approach"
    )
    worst_movement_los: Optional[LOS] = Field(
        default=None,
        description="Worst movement LOS"
    )
    worst_movement_name: Optional[str] = Field(
        default=None,
        description="Name of worst movement"
    )
    lane_groups: list[LaneGroupResult] = Field(
        default_factory=list,
        description="Individual lane group results"
    )
    cycle_length: Optional[float] = Field(
        default=None,
        description="Signal cycle length in seconds"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes"
    )


class ScenarioResult(BaseModel):
    """Results for a complete scenario."""

    scenario_type: ScenarioType = Field(description="Type of scenario")
    scenario_name: str = Field(description="Scenario name")
    year: Optional[int] = Field(default=None, description="Analysis year")
    intersections: list[IntersectionResult] = Field(
        description="Results for each intersection"
    )
    description: Optional[str] = Field(
        default=None,
        description="Scenario description"
    )


class ScenarioComparison(BaseModel):
    """Comparison between two scenarios."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "baseline": {
                    "scenario_type": "Existing",
                    "scenario_name": "Existing Conditions",
                    "intersections": []
                },
                "proposed": {
                    "scenario_type": "Build",
                    "scenario_name": "With Project",
                    "intersections": []
                },
                "project_name": "Proposed Mixed-Use Development",
                "project_trips_am": 150,
                "project_trips_pm": 200
            }
        }
    )

    baseline: ScenarioResult = Field(description="Baseline scenario")
    proposed: ScenarioResult = Field(description="Proposed/build scenario")
    project_name: Optional[str] = Field(
        default=None,
        description="Name of the proposed project"
    )
    project_trips_am: Optional[int] = Field(
        default=None,
        description="Project AM peak hour trips"
    )
    project_trips_pm: Optional[int] = Field(
        default=None,
        description="Project PM peak hour trips"
    )


# --- Output Models ---

class NarrativeSection(BaseModel):
    """A single section of narrative text."""

    section_id: str = Field(description="Section identifier")
    title: str = Field(description="Section title")
    content: str = Field(description="Narrative content")


class ReportNarrative(BaseModel):
    """Complete report narrative output."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sections": [
                    {
                        "section_id": "executive_summary",
                        "title": "Executive Summary",
                        "content": "The traffic analysis..."
                    }
                ],
                "generated_from": "ScenarioComparison",
                "data_hash": "abc123"
            }
        }
    )

    sections: list[NarrativeSection] = Field(
        description="Narrative sections"
    )
    generated_from: str = Field(
        description="Type of input data used"
    )
    data_hash: Optional[str] = Field(
        default=None,
        description="Hash of input data for verification"
    )
