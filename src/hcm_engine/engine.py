"""
Main HCM signalized intersection engine.

Orchestrates the computation pipeline:
    1. Saturation flow calculation
    2. Capacity calculation
    3. v/c ratio
    4. Control delay
    5. LOS classification
"""

from . import __engine_version__
from .models import LaneGroupInput, LaneGroupResult
from .saturation_flow import compute_saturation_flow
from .capacity import compute_capacity, compute_vc_ratio
from .delay import compute_control_delay
from .los import classify_los


def compute_lane_group_results(inputs: LaneGroupInput) -> LaneGroupResult:
    """
    Compute complete results for a lane group.

    This is the main entry point for the HCM signalized intersection engine.
    It performs all calculations in sequence and returns a complete result
    with all intermediate values for auditability.

    Calculation sequence:
        1. Compute saturation flow rate with adjustment factors
        2. Compute capacity (c = s * g/C)
        3. Compute v/c ratio (X = v/c)
        4. Compute control delay (d = d1 + d2)
        5. Classify Level of Service

    Args:
        inputs: Lane group input parameters (validated Pydantic model)

    Returns:
        LaneGroupResult with all computed values

    Example:
        >>> from hcm_engine import compute_lane_group_results, LaneGroupInput, SignalTimingInput
        >>> inputs = LaneGroupInput(
        ...     volume=800,
        ...     num_lanes=2,
        ...     signal_timing=SignalTimingInput(
        ...         cycle_length=90,
        ...         effective_green=40
        ...     )
        ... )
        >>> results = compute_lane_group_results(inputs)
        >>> print(f"LOS: {results.los.value}, Delay: {results.control_delay} sec")
    """
    # Step 1: Compute saturation flow
    sat_flow_result = compute_saturation_flow(inputs)

    # Step 2: Compute capacity
    capacity = compute_capacity(
        saturation_flow=sat_flow_result.total_saturation_flow,
        effective_green=inputs.signal_timing.effective_green,
        cycle_length=inputs.signal_timing.cycle_length
    )

    # Step 3: Compute v/c ratio
    vc_ratio = compute_vc_ratio(
        volume=inputs.volume,
        capacity=capacity
    )

    # Step 4: Compute control delay
    d1, d2, total_delay = compute_control_delay(
        effective_green=inputs.signal_timing.effective_green,
        cycle_length=inputs.signal_timing.cycle_length,
        vc_ratio=vc_ratio,
        capacity=capacity,
        analysis_period_hours=inputs.analysis_period_hours,
        control_type=inputs.signal_timing.control_type,
        upstream_filtering_factor=inputs.upstream_filtering_factor
    )

    # Step 5: Classify LOS
    los = classify_los(total_delay)

    # Build result
    return LaneGroupResult(
        engine_version=__engine_version__,
        volume=inputs.volume,
        num_lanes=inputs.num_lanes,
        saturation_flow=sat_flow_result,
        capacity=capacity,
        vc_ratio=vc_ratio,
        uniform_delay=d1,
        incremental_delay=d2,
        control_delay=total_delay,
        los=los,
        is_oversaturated=vc_ratio > 1.0
    )
