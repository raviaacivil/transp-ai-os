"""
Control delay calculations per HCM 6th Edition.

Reference: HCM 6th Edition, Chapter 19, Equations 19-18 through 19-22

Control delay is the primary performance measure for signalized intersections.
It consists of:
    d = d1 + d2 + d3

Where:
    d1 = uniform delay (assuming uniform arrivals)
    d2 = incremental delay (random + overflow component)
    d3 = initial queue delay (residual queue from prior period)

This implementation covers d1 and d2. d3 requires multi-period analysis.
"""

import math
from .models import SignalControlType


def compute_uniform_delay(
    effective_green: float,
    cycle_length: float,
    vc_ratio: float
) -> float:
    """
    Compute uniform delay (d1).

    HCM 6th Edition Equation 19-18:
    d1 = (0.5 * C * (1 - g/C)^2) / (1 - min(1, X) * g/C)

    Where:
        C = cycle length (seconds)
        g = effective green time (seconds)
        X = v/c ratio

    Uniform delay represents the delay assuming perfectly uniform
    vehicle arrivals and no random variation.

    Args:
        effective_green: Effective green time (seconds)
        cycle_length: Cycle length (seconds)
        vc_ratio: Volume-to-capacity ratio

    Returns:
        Uniform delay in seconds
    """
    if cycle_length <= 0:
        raise ValueError("cycle_length must be positive")

    C = cycle_length
    g = effective_green
    X = vc_ratio

    g_over_C = g / C

    # Use min(1, X) to avoid negative denominator for oversaturated conditions
    X_effective = min(1.0, X)

    numerator = 0.5 * C * (1.0 - g_over_C) ** 2
    denominator = 1.0 - X_effective * g_over_C

    # Prevent division by zero (occurs when X=1 and g=C)
    if denominator <= 0.001:
        denominator = 0.001

    d1 = numerator / denominator

    return round(d1, 2)


def get_incremental_delay_factor(control_type: SignalControlType) -> float:
    """
    Get the incremental delay calibration factor (k).

    HCM 6th Edition Table 19-13:
        Pretimed: k = 0.50
        Actuated uncoordinated: k = 0.50
        Actuated coordinated: k = 0.40 to 0.50

    The k factor accounts for the quality of progression
    and controller type.

    Args:
        control_type: Type of signal control

    Returns:
        Incremental delay factor (k)
    """
    if control_type == SignalControlType.ACTUATED_COORDINATED:
        return 0.45  # Middle of range for coordinated
    return 0.50  # Pretimed or actuated uncoordinated


def compute_incremental_delay(
    vc_ratio: float,
    capacity: float,
    analysis_period_hours: float,
    control_type: SignalControlType,
    upstream_filtering_factor: float = 1.0
) -> float:
    """
    Compute incremental delay (d2).

    HCM 6th Edition Equation 19-19:
    d2 = 900 * T * [(X - 1) + sqrt((X - 1)^2 + (8 * k * I * X) / (c * T))]

    Where:
        T = analysis period (hours)
        X = v/c ratio
        k = incremental delay factor (0.50 for pretimed)
        I = upstream filtering adjustment (1.0 for isolated)
        c = capacity (veh/h)

    Incremental delay accounts for:
        - Random arrival variations
        - Overflow delay when X > 1

    Args:
        vc_ratio: Volume-to-capacity ratio
        capacity: Capacity (veh/h)
        analysis_period_hours: Analysis period (hours, typically 0.25)
        control_type: Type of signal control
        upstream_filtering_factor: Upstream filtering adjustment (I)

    Returns:
        Incremental delay in seconds
    """
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    if analysis_period_hours <= 0:
        raise ValueError("analysis_period_hours must be positive")

    X = vc_ratio
    c = capacity
    T = analysis_period_hours
    k = get_incremental_delay_factor(control_type)
    I = upstream_filtering_factor

    # The term inside the square root
    term1 = (X - 1.0)
    term2 = (X - 1.0) ** 2
    term3 = (8.0 * k * I * X) / (c * T)

    # sqrt term
    sqrt_term = math.sqrt(term2 + term3)

    d2 = 900.0 * T * (term1 + sqrt_term)

    # d2 should never be negative
    d2 = max(0.0, d2)

    return round(d2, 2)


def compute_control_delay(
    effective_green: float,
    cycle_length: float,
    vc_ratio: float,
    capacity: float,
    analysis_period_hours: float,
    control_type: SignalControlType,
    upstream_filtering_factor: float = 1.0
) -> tuple[float, float, float]:
    """
    Compute total control delay.

    HCM 6th Edition:
    d = d1 + d2 (+ d3, not implemented)

    Note: This implementation does not include initial queue delay (d3),
    which requires multi-period analysis to determine residual queues.

    Args:
        effective_green: Effective green time (seconds)
        cycle_length: Cycle length (seconds)
        vc_ratio: Volume-to-capacity ratio
        capacity: Capacity (veh/h)
        analysis_period_hours: Analysis period (hours)
        control_type: Type of signal control
        upstream_filtering_factor: Upstream filtering adjustment (I)

    Returns:
        Tuple of (uniform_delay, incremental_delay, total_control_delay)
        All values in seconds
    """
    d1 = compute_uniform_delay(
        effective_green=effective_green,
        cycle_length=cycle_length,
        vc_ratio=vc_ratio
    )

    d2 = compute_incremental_delay(
        vc_ratio=vc_ratio,
        capacity=capacity,
        analysis_period_hours=analysis_period_hours,
        control_type=control_type,
        upstream_filtering_factor=upstream_filtering_factor
    )

    total_delay = d1 + d2

    return (d1, d2, round(total_delay, 2))
