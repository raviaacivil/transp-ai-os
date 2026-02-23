"""HCM computation endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.hcm_engine import (
    compute_lane_group_results,
    LaneGroupInput,
    LaneGroupResult,
    __engine_version__,
)

router = APIRouter()


class ComputeLOSRequest(BaseModel):
    """Request body for LOS computation."""

    lane_group: LaneGroupInput = Field(
        ...,
        description="Lane group input parameters"
    )


class ComputeLOSResponse(BaseModel):
    """Response for LOS computation."""

    success: bool = Field(description="Whether computation succeeded")
    result: LaneGroupResult = Field(description="Computation results")


class EngineInfoResponse(BaseModel):
    """Response for engine info endpoint."""

    engine_version: str = Field(description="HCM engine version")
    description: str = Field(description="Engine description")


@router.get("/info", response_model=EngineInfoResponse)
async def get_engine_info() -> EngineInfoResponse:
    """Get HCM engine information."""
    return EngineInfoResponse(
        engine_version=__engine_version__,
        description="HCM 6th Edition Signalized Intersection Engine"
    )


@router.post("/compute-los", response_model=ComputeLOSResponse)
async def compute_los(request: ComputeLOSRequest) -> ComputeLOSResponse:
    """
    Compute Level of Service for a signalized intersection lane group.

    This endpoint performs deterministic HCM 6th Edition calculations:
    - Saturation flow rate with adjustment factors
    - Capacity (c = s × g/C)
    - Volume-to-capacity ratio
    - Control delay (uniform + incremental)
    - LOS classification (A-F)

    Returns complete results including all intermediate values for auditability.
    """
    result = compute_lane_group_results(request.lane_group)
    return ComputeLOSResponse(success=True, result=result)
