"""
Pydantic models for scenario versioning.

Follows JSON Patch (RFC 6902) style structure with domain-specific extensions.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class ChangeOperation(str, Enum):
    """
    Supported change operations.

    Core operations follow JSON Patch semantics.
    Domain operations provide transportation-specific shortcuts.
    """

    # Core operations (JSON Patch style)
    REPLACE = "replace"
    ADD = "add"
    REMOVE = "remove"

    # Domain-specific operations
    ADD_LANE = "add_lane"
    REMOVE_LANE = "remove_lane"
    MODIFY_LANES = "modify_lanes"
    MODIFY_VOLUME = "modify_volume"
    MODIFY_TIMING = "modify_timing"


class ScenarioChange(BaseModel):
    """
    A single change operation.

    Follows JSON Patch structure:
        - op: The operation to perform
        - path: JSON Pointer to the target location
        - value: The new value (for add/replace operations)

    Examples:
        Replace volume:
            {"op": "replace", "path": "/volume", "value": 1200}

        Add lane:
            {"op": "add_lane", "path": "/lane_groups/0", "value": {"movement_type": "through"}}

        Modify lanes:
            {"op": "modify_lanes", "path": "/lane_groups/0", "value": 3}
    """

    op: ChangeOperation = Field(
        ...,
        description="The operation to perform"
    )
    path: str = Field(
        ...,
        description="JSON Pointer path to target (e.g., '/volume', '/lane_groups/0/num_lanes')"
    )
    value: Any = Field(
        default=None,
        description="The new value (required for add/replace operations)"
    )
    previous_value: Optional[Any] = Field(
        default=None,
        description="Previous value (populated after apply for audit)"
    )

    @field_validator("path")
    @classmethod
    def validate_path_format(cls, v: str) -> str:
        """Path must start with /."""
        if not v.startswith("/"):
            raise ValueError("path must start with '/'")
        return v


class ScenarioChangeSet(BaseModel):
    """
    A collection of changes to apply atomically.

    Changes are applied in order. If any change fails validation,
    the entire changeset is rejected (no partial application).
    """

    scenario_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for this scenario"
    )
    name: Optional[str] = Field(
        default=None,
        description="Human-readable scenario name"
    )
    description: Optional[str] = Field(
        default=None,
        description="Description of what this scenario represents"
    )
    changes: list[ScenarioChange] = Field(
        default_factory=list,
        description="Ordered list of changes to apply"
    )
    parent_scenario_id: Optional[str] = Field(
        default=None,
        description="Parent scenario ID (for scenario branching)"
    )

    def add_change(
        self,
        op: ChangeOperation,
        path: str,
        value: Any = None
    ) -> "ScenarioChangeSet":
        """Add a change to the changeset (fluent interface)."""
        self.changes.append(ScenarioChange(op=op, path=path, value=value))
        return self


class ValidationError(BaseModel):
    """Validation error details."""

    path: str = Field(description="Path that failed validation")
    message: str = Field(description="Error message")
    change_index: int = Field(description="Index of the failing change")


class ChangeResult(BaseModel):
    """Result of applying a changeset."""

    success: bool = Field(description="Whether all changes were applied")
    changes_applied: int = Field(description="Number of changes applied")
    errors: list[ValidationError] = Field(
        default_factory=list,
        description="Validation errors (if any)"
    )
    modified_object: Optional[dict[str, Any]] = Field(
        default=None,
        description="The modified object (if successful)"
    )
    applied_changes: list[ScenarioChange] = Field(
        default_factory=list,
        description="Changes with previous_value populated"
    )
