"""
Pydantic models for HCM signalized intersection calculations.

All inputs and outputs are strongly typed with validation.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class LevelOfService(str, Enum):
    """HCM Level of Service grades for signalized intersections."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class MovementType(str, Enum):
    """Lane group movement types."""
    THROUGH = "through"
    LEFT = "left"
    RIGHT = "right"
    THROUGH_RIGHT = "through_right"
    THROUGH_LEFT = "through_left"
    LEFT_RIGHT = "left_right"
    ALL = "all"


class SignalControlType(str, Enum):
    """Signal control type for delay calculations."""
    PRETIMED = "pretimed"
    ACTUATED_UNCOORDINATED = "actuated_uncoordinated"
    ACTUATED_COORDINATED = "actuated_coordinated"


class SignalTimingInput(BaseModel):
    """Signal timing parameters for a lane group."""

    cycle_length: float = Field(
        ...,
        gt=0,
        le=300,
        description="Cycle length in seconds"
    )
    effective_green: float = Field(
        ...,
        gt=0,
        description="Effective green time in seconds"
    )
    control_type: SignalControlType = Field(
        default=SignalControlType.PRETIMED,
        description="Type of signal control"
    )

    @field_validator("effective_green")
    @classmethod
    def green_must_be_less_than_cycle(cls, v, info):
        """Effective green cannot exceed cycle length."""
        cycle = info.data.get("cycle_length")
        if cycle is not None and v > cycle:
            raise ValueError("effective_green cannot exceed cycle_length")
        return v


class LaneGroupInput(BaseModel):
    """Input parameters for a single lane group."""

    # Volume
    volume: float = Field(
        ...,
        ge=0,
        description="Demand volume in vehicles per hour (vph)"
    )

    # Lane configuration
    num_lanes: int = Field(
        ...,
        ge=1,
        le=8,
        description="Number of lanes in the lane group"
    )
    movement_type: MovementType = Field(
        default=MovementType.THROUGH,
        description="Type of movement"
    )

    # Saturation flow adjustments
    base_saturation_flow: float = Field(
        default=1900.0,
        gt=0,
        description="Base saturation flow rate (pc/h/ln)"
    )
    lane_width: float = Field(
        default=12.0,
        gt=8.0,
        le=24.0,
        description="Lane width in feet"
    )
    heavy_vehicle_pct: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Percent heavy vehicles"
    )
    grade_pct: float = Field(
        default=0.0,
        ge=-10,
        le=10,
        description="Approach grade in percent (negative = downhill)"
    )
    parking_adjacent: bool = Field(
        default=False,
        description="Whether parking is adjacent to lane group"
    )
    parking_maneuvers_per_hour: float = Field(
        default=0.0,
        ge=0,
        description="Parking maneuvers per hour (if parking_adjacent)"
    )
    bus_stops_per_hour: float = Field(
        default=0.0,
        ge=0,
        description="Bus stopping events per hour"
    )
    area_type: str = Field(
        default="other",
        pattern="^(cbd|other)$",
        description="Area type: 'cbd' or 'other'"
    )

    # Turn-specific factors (used for left/right movements)
    left_turn_pct: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Percent left turns in shared lane group"
    )
    right_turn_pct: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Percent right turns in shared lane group"
    )

    # Signal timing
    signal_timing: SignalTimingInput = Field(
        ...,
        description="Signal timing for this lane group"
    )

    # Analysis period
    analysis_period_hours: float = Field(
        default=0.25,
        gt=0,
        le=1,
        description="Analysis period in hours (typically 0.25 for 15-min)"
    )

    # Upstream filtering (for coordinated systems)
    upstream_filtering_factor: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Upstream filtering/metering adjustment factor (I)"
    )


class SaturationFlowResult(BaseModel):
    """Result of saturation flow calculation with breakdown."""

    base_saturation_flow: float = Field(
        description="Base saturation flow (pc/h/ln)"
    )
    adjusted_saturation_flow: float = Field(
        description="Adjusted saturation flow (veh/h/ln)"
    )
    total_saturation_flow: float = Field(
        description="Total saturation flow for lane group (veh/h)"
    )

    # Adjustment factors applied
    f_w: float = Field(description="Lane width factor")
    f_hv: float = Field(description="Heavy vehicle factor")
    f_g: float = Field(description="Grade factor")
    f_p: float = Field(description="Parking factor")
    f_bb: float = Field(description="Bus blockage factor")
    f_a: float = Field(description="Area type factor")
    f_lt: float = Field(description="Left turn factor")
    f_rt: float = Field(description="Right turn factor")


class LaneGroupResult(BaseModel):
    """Complete result for a lane group analysis."""

    # Engine metadata
    engine_version: str = Field(
        description="Version of the HCM engine used"
    )

    # Input echo (for audit)
    volume: float = Field(description="Input volume (vph)")
    num_lanes: int = Field(description="Number of lanes")

    # Saturation flow
    saturation_flow: SaturationFlowResult = Field(
        description="Saturation flow calculation details"
    )

    # Capacity
    capacity: float = Field(
        description="Capacity in vehicles per hour (vph)"
    )

    # Volume to capacity
    vc_ratio: float = Field(
        description="Volume-to-capacity ratio (X)"
    )

    # Delay components
    uniform_delay: float = Field(
        description="Uniform delay d1 (seconds)"
    )
    incremental_delay: float = Field(
        description="Incremental delay d2 (seconds)"
    )
    control_delay: float = Field(
        description="Total control delay (seconds)"
    )

    # Level of Service
    los: LevelOfService = Field(
        description="Level of Service grade"
    )

    # Status flags
    is_oversaturated: bool = Field(
        description="True if v/c > 1.0"
    )
