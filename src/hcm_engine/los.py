"""
Level of Service (LOS) classification per HCM 6th Edition.

Reference: HCM 6th Edition, Chapter 19, Exhibit 19-8
"""

from .models import LevelOfService


# LOS thresholds for signalized intersections (control delay in seconds)
# HCM 6th Edition Exhibit 19-8
LOS_THRESHOLDS = {
    LevelOfService.A: 10.0,    # delay <= 10 sec
    LevelOfService.B: 20.0,    # delay <= 20 sec
    LevelOfService.C: 35.0,    # delay <= 35 sec
    LevelOfService.D: 55.0,    # delay <= 55 sec
    LevelOfService.E: 80.0,    # delay <= 80 sec
    # LevelOfService.F: > 80 sec
}


def classify_los(control_delay: float) -> LevelOfService:
    """
    Classify Level of Service based on control delay.

    HCM 6th Edition Exhibit 19-8:
        LOS A: delay <= 10 sec
        LOS B: 10 < delay <= 20 sec
        LOS C: 20 < delay <= 35 sec
        LOS D: 35 < delay <= 55 sec
        LOS E: 55 < delay <= 80 sec
        LOS F: delay > 80 sec

    Args:
        control_delay: Control delay in seconds

    Returns:
        Level of Service grade

    Raises:
        ValueError: If control_delay is negative
    """
    if control_delay < 0:
        raise ValueError("control_delay cannot be negative")

    if control_delay <= LOS_THRESHOLDS[LevelOfService.A]:
        return LevelOfService.A
    elif control_delay <= LOS_THRESHOLDS[LevelOfService.B]:
        return LevelOfService.B
    elif control_delay <= LOS_THRESHOLDS[LevelOfService.C]:
        return LevelOfService.C
    elif control_delay <= LOS_THRESHOLDS[LevelOfService.D]:
        return LevelOfService.D
    elif control_delay <= LOS_THRESHOLDS[LevelOfService.E]:
        return LevelOfService.E
    else:
        return LevelOfService.F


def get_los_description(los: LevelOfService) -> str:
    """
    Get a human-readable description for a LOS grade.

    Args:
        los: Level of Service grade

    Returns:
        Description of the LOS grade
    """
    descriptions = {
        LevelOfService.A: "Free-flow operations",
        LevelOfService.B: "Stable flow with slight delays",
        LevelOfService.C: "Stable flow with acceptable delays",
        LevelOfService.D: "Approaching unstable flow",
        LevelOfService.E: "Unstable flow, at capacity",
        LevelOfService.F: "Oversaturated, forced flow",
    }
    return descriptions[los]
