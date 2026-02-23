"""
Scenario Versioning Engine

Provides structured diff-based modifications to transportation objects.
Supports JSON Patch style operations for reproducible scenario management.
"""

__version__ = "0.1.0"

from .models import (
    ChangeOperation,
    ScenarioChange,
    ScenarioChangeSet,
    ChangeResult,
    ValidationError,
)
from .service import (
    apply_changes,
    validate_changes,
    compute_diff,
)

__all__ = [
    "__version__",
    "ChangeOperation",
    "ScenarioChange",
    "ScenarioChangeSet",
    "ChangeResult",
    "ValidationError",
    "apply_changes",
    "validate_changes",
    "compute_diff",
]
