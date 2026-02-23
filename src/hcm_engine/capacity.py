"""
Capacity calculations per HCM 6th Edition.

Reference: HCM 6th Edition, Chapter 19
"""


def compute_capacity(
    saturation_flow: float,
    effective_green: float,
    cycle_length: float
) -> float:
    """
    Compute lane group capacity.

    HCM 6th Edition Equation 19-15:
    c = s * (g/C)

    Where:
        c = capacity (veh/h)
        s = saturation flow rate (veh/h)
        g = effective green time (seconds)
        C = cycle length (seconds)

    Args:
        saturation_flow: Total saturation flow for lane group (veh/h)
        effective_green: Effective green time (seconds)
        cycle_length: Cycle length (seconds)

    Returns:
        Capacity in vehicles per hour

    Raises:
        ValueError: If inputs are invalid
    """
    if cycle_length <= 0:
        raise ValueError("cycle_length must be positive")
    if effective_green < 0:
        raise ValueError("effective_green cannot be negative")
    if effective_green > cycle_length:
        raise ValueError("effective_green cannot exceed cycle_length")
    if saturation_flow < 0:
        raise ValueError("saturation_flow cannot be negative")

    g_over_c = effective_green / cycle_length
    capacity = saturation_flow * g_over_c

    return round(capacity, 1)


def compute_vc_ratio(volume: float, capacity: float) -> float:
    """
    Compute volume-to-capacity ratio (X).

    HCM 6th Edition:
    X = v/c

    Where:
        v = demand volume (veh/h)
        c = capacity (veh/h)

    The v/c ratio indicates the degree of saturation:
        X < 1.0: Undersaturated (demand less than capacity)
        X = 1.0: At capacity
        X > 1.0: Oversaturated (demand exceeds capacity)

    Args:
        volume: Demand volume in vehicles per hour
        capacity: Capacity in vehicles per hour

    Returns:
        Volume-to-capacity ratio (can exceed 1.0)

    Raises:
        ValueError: If capacity is zero or negative
    """
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    if volume < 0:
        raise ValueError("volume cannot be negative")

    vc_ratio = volume / capacity

    return round(vc_ratio, 4)
