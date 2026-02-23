"""
Saturation flow rate calculations per HCM 6th Edition.

Reference: HCM 6th Edition, Chapter 19, Exhibit 19-11

The saturation flow rate represents the maximum flow that can pass through
a lane group during the effective green time.
"""

from .models import LaneGroupInput, SaturationFlowResult, MovementType


def compute_lane_width_factor(lane_width: float) -> float:
    """
    Compute lane width adjustment factor (fw).

    HCM 6th Edition Equation 19-8:
    fw = 1 + (W - 12) / 30

    Where W is the average lane width in feet.

    Note: For lane widths < 12 ft, fw < 1.0 (reduces saturation flow).
          For lane widths > 12 ft, fw > 1.0 (increases saturation flow).

    Args:
        lane_width: Lane width in feet (must be > 8, typically 10-14)

    Returns:
        Lane width factor (typically 0.87 to 1.07)
    """
    fw = 1.0 + (lane_width - 12.0) / 30.0
    # Bound the factor to reasonable limits per HCM guidance
    return max(0.87, min(fw, 1.07))


def compute_heavy_vehicle_factor(heavy_vehicle_pct: float) -> float:
    """
    Compute heavy vehicle adjustment factor (fHV).

    HCM 6th Edition Equation 19-9:
    fHV = 100 / (100 + %HV * (ET - 1))

    Where ET = 2.0 for typical heavy vehicles (passenger car equivalent).

    Args:
        heavy_vehicle_pct: Percentage of heavy vehicles (0-100)

    Returns:
        Heavy vehicle factor (1.0 for 0% HV, decreasing with more HV)
    """
    ET = 2.0  # Passenger car equivalent for heavy vehicles
    pct = heavy_vehicle_pct / 100.0
    fhv = 100.0 / (100.0 + heavy_vehicle_pct * (ET - 1.0))
    return fhv


def compute_grade_factor(grade_pct: float) -> float:
    """
    Compute grade adjustment factor (fg).

    HCM 6th Edition Equation 19-10:
    fg = 1 - (%G / 200)

    Where %G is the approach grade (negative for downhill).

    Note: Positive grade (uphill) reduces saturation flow.
          Negative grade (downhill) increases saturation flow.

    Args:
        grade_pct: Grade in percent (-10 to +10 typical)

    Returns:
        Grade factor (0.95 to 1.05 typical)
    """
    fg = 1.0 - (grade_pct / 200.0)
    return fg


def compute_parking_factor(
    parking_adjacent: bool,
    parking_maneuvers_per_hour: float,
    num_lanes: int
) -> float:
    """
    Compute parking adjustment factor (fp).

    HCM 6th Edition Equation 19-11:
    fp = (N - 0.1 - (18 * Nm / 3600)) / N

    Where:
        N = number of lanes
        Nm = parking maneuvers per hour

    If no parking, fp = 1.0

    Args:
        parking_adjacent: Whether parking is adjacent to the lane group
        parking_maneuvers_per_hour: Number of parking maneuvers per hour
        num_lanes: Number of lanes in the lane group

    Returns:
        Parking factor (≤ 1.0)
    """
    if not parking_adjacent or parking_maneuvers_per_hour == 0:
        return 1.0

    N = num_lanes
    Nm = parking_maneuvers_per_hour

    fp = (N - 0.1 - (18.0 * Nm / 3600.0)) / N
    # fp must be >= 0.05 per HCM guidance
    return max(0.05, min(fp, 1.0))


def compute_bus_blockage_factor(
    bus_stops_per_hour: float,
    num_lanes: int
) -> float:
    """
    Compute bus blockage adjustment factor (fbb).

    HCM 6th Edition Equation 19-12:
    fbb = (N - (14.4 * Nb / 3600)) / N

    Where:
        N = number of lanes
        Nb = bus stopping events per hour

    Args:
        bus_stops_per_hour: Number of bus stops per hour
        num_lanes: Number of lanes

    Returns:
        Bus blockage factor (≤ 1.0)
    """
    if bus_stops_per_hour == 0:
        return 1.0

    N = num_lanes
    Nb = bus_stops_per_hour

    fbb = (N - (14.4 * Nb / 3600.0)) / N
    # fbb must be >= 0.05 per HCM guidance
    return max(0.05, min(fbb, 1.0))


def compute_area_type_factor(area_type: str) -> float:
    """
    Compute area type adjustment factor (fa).

    HCM 6th Edition: fa = 0.90 for CBD, 1.00 for other areas.

    CBD areas have more pedestrian activity, narrower streets,
    and more complex driver decisions.

    Args:
        area_type: 'cbd' or 'other'

    Returns:
        Area type factor (0.90 or 1.00)
    """
    if area_type.lower() == "cbd":
        return 0.90
    return 1.00


def compute_left_turn_factor(
    movement_type: MovementType,
    left_turn_pct: float
) -> float:
    """
    Compute left turn adjustment factor (fLT).

    Simplified HCM approach for protected phases:
    - Exclusive left turn lane: fLT = 0.95
    - Shared lane: fLT = 1 / (1 + 0.05 * PLT)

    Where PLT is the proportion of left turns.

    NOTE: This is a simplified model. Full HCM includes
    protected-permitted phasing and pedestrian conflicts.

    Args:
        movement_type: Type of movement
        left_turn_pct: Percentage of left turns

    Returns:
        Left turn factor (≤ 1.0)
    """
    if movement_type == MovementType.LEFT:
        # Exclusive left turn lane (protected phase assumed)
        return 0.95

    if movement_type in (MovementType.THROUGH_LEFT, MovementType.ALL):
        # Shared lane with through traffic
        PLT = left_turn_pct / 100.0
        flt = 1.0 / (1.0 + 0.05 * PLT)
        return flt

    # No left turns in this lane group
    return 1.0


def compute_right_turn_factor(
    movement_type: MovementType,
    right_turn_pct: float
) -> float:
    """
    Compute right turn adjustment factor (fRT).

    Simplified HCM approach:
    - Exclusive right turn lane: fRT = 0.85
    - Shared lane: fRT = 1 - 0.15 * PRT

    Where PRT is the proportion of right turns.

    NOTE: This is a simplified model. Full HCM includes
    pedestrian conflict adjustments.

    Args:
        movement_type: Type of movement
        right_turn_pct: Percentage of right turns

    Returns:
        Right turn factor (≤ 1.0)
    """
    if movement_type == MovementType.RIGHT:
        # Exclusive right turn lane
        return 0.85

    if movement_type in (
        MovementType.THROUGH_RIGHT,
        MovementType.LEFT_RIGHT,
        MovementType.ALL
    ):
        # Shared lane with right turns
        PRT = right_turn_pct / 100.0
        frt = 1.0 - 0.15 * PRT
        return max(0.05, frt)

    # No right turns in this lane group
    return 1.0


def compute_saturation_flow(inputs: LaneGroupInput) -> SaturationFlowResult:
    """
    Compute adjusted saturation flow rate for a lane group.

    HCM 6th Edition Equation 19-8:
    s = s0 * N * fw * fHV * fg * fp * fbb * fa * fLT * fRT

    Where:
        s0 = base saturation flow rate (pc/h/ln)
        N = number of lanes
        fw = lane width factor
        fHV = heavy vehicle factor
        fg = grade factor
        fp = parking factor
        fbb = bus blockage factor
        fa = area type factor
        fLT = left turn factor
        fRT = right turn factor

    Note: Pedestrian and bicycle adjustments (fLpb, fRpb) are not
    included in this simplified implementation.

    Args:
        inputs: Lane group input parameters

    Returns:
        SaturationFlowResult with all factors and final saturation flow
    """
    s0 = inputs.base_saturation_flow

    # Compute all adjustment factors
    f_w = compute_lane_width_factor(inputs.lane_width)
    f_hv = compute_heavy_vehicle_factor(inputs.heavy_vehicle_pct)
    f_g = compute_grade_factor(inputs.grade_pct)
    f_p = compute_parking_factor(
        inputs.parking_adjacent,
        inputs.parking_maneuvers_per_hour,
        inputs.num_lanes
    )
    f_bb = compute_bus_blockage_factor(
        inputs.bus_stops_per_hour,
        inputs.num_lanes
    )
    f_a = compute_area_type_factor(inputs.area_type)
    f_lt = compute_left_turn_factor(
        inputs.movement_type,
        inputs.left_turn_pct
    )
    f_rt = compute_right_turn_factor(
        inputs.movement_type,
        inputs.right_turn_pct
    )

    # Adjusted saturation flow per lane
    s_adjusted = s0 * f_w * f_hv * f_g * f_p * f_bb * f_a * f_lt * f_rt

    # Total saturation flow for lane group
    s_total = s_adjusted * inputs.num_lanes

    return SaturationFlowResult(
        base_saturation_flow=s0,
        adjusted_saturation_flow=round(s_adjusted, 1),
        total_saturation_flow=round(s_total, 1),
        f_w=round(f_w, 4),
        f_hv=round(f_hv, 4),
        f_g=round(f_g, 4),
        f_p=round(f_p, 4),
        f_bb=round(f_bb, 4),
        f_a=round(f_a, 4),
        f_lt=round(f_lt, 4),
        f_rt=round(f_rt, 4),
    )
