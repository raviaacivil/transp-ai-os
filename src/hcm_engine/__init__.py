"""
HCM 6th Edition Signalized Intersection Engine

Deterministic capacity and delay calculations per Highway Capacity Manual methodology.
"""

__version__ = "0.1.0"
__engine_version__ = "HCM6-SIG-0.1.0"

from .engine import compute_lane_group_results
from .models import (
    LaneGroupInput,
    SignalTimingInput,
    LaneGroupResult,
    LevelOfService,
)

__all__ = [
    "__version__",
    "__engine_version__",
    "compute_lane_group_results",
    "LaneGroupInput",
    "SignalTimingInput",
    "LaneGroupResult",
    "LevelOfService",
]
