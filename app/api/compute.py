"""
Compute endpoints for traffic analysis.

These endpoints perform deterministic HCM calculations.
No database persistence - computation only.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict

from src.hcm_engine import (
    compute_lane_group_results,
    LaneGroupInput,
    LaneGroupResult,
    SignalTimingInput,
    __engine_version__,
)
from src.hcm_engine.models import MovementType, SignalControlType

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Request/Response Models ---

class SignalizedRequest(BaseModel):
    """
    Request body for signalized intersection LOS computation.

    Provide lane group parameters and signal timing to compute
    capacity, delay, and Level of Service per HCM 6th Edition.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "volume": 850,
                "num_lanes": 2,
                "movement_type": "through",
                "lane_width": 12.0,
                "heavy_vehicle_pct": 5.0,
                "grade_pct": 0.0,
                "area_type": "other",
                "signal_timing": {
                    "cycle_length": 90,
                    "effective_green": 42,
                    "control_type": "pretimed"
                }
            }
        }
    )

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
        description="Type of movement (through, left, right, etc.)"
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
        description="Approach grade in percent"
    )
    parking_adjacent: bool = Field(
        default=False,
        description="Whether parking is adjacent to lane group"
    )
    parking_maneuvers_per_hour: float = Field(
        default=0.0,
        ge=0,
        description="Parking maneuvers per hour"
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

    # Turn percentages for shared lanes
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

    # Signal timing (nested)
    signal_timing: "SignalTimingRequest" = Field(
        ...,
        description="Signal timing parameters"
    )

    # Analysis parameters
    analysis_period_hours: float = Field(
        default=0.25,
        gt=0,
        le=1,
        description="Analysis period in hours (default 0.25 = 15 min)"
    )
    upstream_filtering_factor: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Upstream filtering factor (I), 1.0 for isolated"
    )


class SignalTimingRequest(BaseModel):
    """Signal timing parameters."""

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
        description="Signal control type"
    )


# Update forward reference
SignalizedRequest.model_rebuild()


class SignalizedResponse(BaseModel):
    """
    Response for signalized intersection computation.

    Contains complete results including all intermediate values
    for auditability and verification.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "engine_version": "HCM6-SIG-0.1.0",
                "volume": 850,
                "num_lanes": 2,
                "capacity": 1775.6,
                "vc_ratio": 0.4787,
                "uniform_delay": 18.42,
                "incremental_delay": 0.85,
                "control_delay": 19.27,
                "los": "B",
                "is_oversaturated": False,
                "saturation_flow": {
                    "base_saturation_flow": 1900.0,
                    "adjusted_saturation_flow": 1862.5,
                    "total_saturation_flow": 3725.0,
                    "f_w": 1.0,
                    "f_hv": 0.9524,
                    "f_g": 1.0,
                    "f_p": 1.0,
                    "f_bb": 1.0,
                    "f_a": 1.0,
                    "f_lt": 1.0,
                    "f_rt": 1.0
                }
            }
        }
    )

    engine_version: str
    volume: float
    num_lanes: int
    capacity: float
    vc_ratio: float
    uniform_delay: float
    incremental_delay: float
    control_delay: float
    los: str
    is_oversaturated: bool
    saturation_flow: dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    detail: Any = Field(default=None, description="Additional error details")


# --- Endpoints ---

@router.post(
    "/signalized",
    response_model=SignalizedResponse,
    responses={
        200: {"description": "Computation successful"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Computation error"},
    },
    summary="Compute signalized intersection LOS",
    description="""
Compute Level of Service for a signalized intersection lane group
using HCM 6th Edition methodology.

**Calculations performed:**
- Saturation flow rate with adjustment factors
- Capacity: c = s × (g/C)
- Volume-to-capacity ratio: X = v/c
- Control delay: d = d₁ + d₂
- LOS classification: A through F

**Notes:**
- All calculations are deterministic
- No database persistence
- Results include all intermediate values for audit
""",
)
async def compute_signalized(request: SignalizedRequest) -> SignalizedResponse:
    """
    Compute LOS for a signalized intersection lane group.

    Returns capacity, v/c ratio, delay, and LOS per HCM 6th Edition.
    """
    logger.info(
        "Computing signalized LOS | engine=%s volume=%s lanes=%s",
        __engine_version__,
        request.volume,
        request.num_lanes,
    )

    try:
        # Convert request to engine input model
        engine_input = LaneGroupInput(
            volume=request.volume,
            num_lanes=request.num_lanes,
            movement_type=request.movement_type,
            base_saturation_flow=request.base_saturation_flow,
            lane_width=request.lane_width,
            heavy_vehicle_pct=request.heavy_vehicle_pct,
            grade_pct=request.grade_pct,
            parking_adjacent=request.parking_adjacent,
            parking_maneuvers_per_hour=request.parking_maneuvers_per_hour,
            bus_stops_per_hour=request.bus_stops_per_hour,
            area_type=request.area_type,
            left_turn_pct=request.left_turn_pct,
            right_turn_pct=request.right_turn_pct,
            signal_timing=SignalTimingInput(
                cycle_length=request.signal_timing.cycle_length,
                effective_green=request.signal_timing.effective_green,
                control_type=request.signal_timing.control_type,
            ),
            analysis_period_hours=request.analysis_period_hours,
            upstream_filtering_factor=request.upstream_filtering_factor,
        )

        # Run deterministic computation
        result = compute_lane_group_results(engine_input)

        logger.info(
            "Computation complete | los=%s vc_ratio=%.3f delay=%.1f",
            result.los.value,
            result.vc_ratio,
            result.control_delay,
        )

        # Convert to response
        return SignalizedResponse(
            engine_version=result.engine_version,
            volume=result.volume,
            num_lanes=result.num_lanes,
            capacity=result.capacity,
            vc_ratio=result.vc_ratio,
            uniform_delay=result.uniform_delay,
            incremental_delay=result.incremental_delay,
            control_delay=result.control_delay,
            los=result.los.value,
            is_oversaturated=result.is_oversaturated,
            saturation_flow=result.saturation_flow.model_dump(),
        )

    except ValueError as e:
        logger.error("Validation error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "validation_error", "message": str(e)},
        )
    except Exception as e:
        logger.exception("Computation error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "computation_error", "message": str(e)},
        )
