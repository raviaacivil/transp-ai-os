"""
Scenario versioning service.

Main entry point for applying structured changes to transportation objects.
Provides atomic changeset application with full audit trail.
"""

from copy import deepcopy
from typing import Any

from .models import (
    ChangeOperation,
    ScenarioChange,
    ScenarioChangeSet,
    ChangeResult,
    ValidationError,
)
from .operations import apply_operation, get_value_at_path
from .validation import validate_change


def validate_changes(
    obj: dict[str, Any],
    changeset: ScenarioChangeSet
) -> list[ValidationError]:
    """
    Validate all changes in a changeset without applying them.

    This performs a "dry run" validation to catch errors before
    any modifications are made.

    Args:
        obj: The base object to validate against
        changeset: The changeset to validate

    Returns:
        List of validation errors (empty if all valid)

    Example:
        >>> errors = validate_changes(intersection, changeset)
        >>> if errors:
        ...     for err in errors:
        ...         print(f"Error at {err.path}: {err.message}")
    """
    all_errors: list[ValidationError] = []

    # Simulate applying changes to catch cascading issues
    current = deepcopy(obj)

    for i, change in enumerate(changeset.changes):
        errors = validate_change(current, change, i)
        all_errors.extend(errors)

        # If this change is valid, apply it to current for next validation
        if not errors:
            try:
                current, _ = apply_operation(current, change)
            except Exception as e:
                all_errors.append(ValidationError(
                    path=change.path,
                    message=f"Simulation failed: {e}",
                    change_index=i
                ))

    return all_errors


def apply_changes(
    obj: dict[str, Any],
    changeset: ScenarioChangeSet,
    validate: bool = True
) -> ChangeResult:
    """
    Apply a changeset to an object.

    Changes are applied atomically - if any change fails,
    the entire changeset is rejected and the original object
    is unchanged.

    Args:
        obj: The base object to modify
        changeset: The changeset to apply
        validate: Whether to validate before applying (default True)

    Returns:
        ChangeResult with success status and modified object

    Example:
        >>> changeset = ScenarioChangeSet(changes=[
        ...     ScenarioChange(op="modify_volume", path="/volume", value=1200),
        ...     ScenarioChange(op="modify_lanes", path="/lane_groups/0", value=3),
        ... ])
        >>> result = apply_changes(intersection, changeset)
        >>> if result.success:
        ...     new_intersection = result.modified_object
    """
    # Validate first if requested
    if validate:
        errors = validate_changes(obj, changeset)
        if errors:
            return ChangeResult(
                success=False,
                changes_applied=0,
                errors=errors,
                modified_object=None,
                applied_changes=[]
            )

    # Apply changes
    current = deepcopy(obj)
    applied_changes: list[ScenarioChange] = []

    try:
        for change in changeset.changes:
            new_state, previous_value = apply_operation(current, change)

            # Record the change with previous value for audit
            applied_change = ScenarioChange(
                op=change.op,
                path=change.path,
                value=change.value,
                previous_value=previous_value
            )
            applied_changes.append(applied_change)

            current = new_state

    except Exception as e:
        return ChangeResult(
            success=False,
            changes_applied=len(applied_changes),
            errors=[ValidationError(
                path=changeset.changes[len(applied_changes)].path,
                message=str(e),
                change_index=len(applied_changes)
            )],
            modified_object=None,
            applied_changes=applied_changes
        )

    return ChangeResult(
        success=True,
        changes_applied=len(applied_changes),
        errors=[],
        modified_object=current,
        applied_changes=applied_changes
    )


def compute_diff(
    original: dict[str, Any],
    modified: dict[str, Any],
    path: str = ""
) -> list[ScenarioChange]:
    """
    Compute the differences between two object states.

    Generates a list of changes that would transform the original
    object into the modified object. Useful for:
    - Creating scenarios from manual edits
    - Comparing scenario results
    - Audit logging

    Args:
        original: The original object state
        modified: The modified object state
        path: Current path prefix (used for recursion)

    Returns:
        List of ScenarioChange objects representing the differences

    Example:
        >>> original = {"volume": 800, "num_lanes": 2}
        >>> modified = {"volume": 1000, "num_lanes": 2}
        >>> changes = compute_diff(original, modified)
        >>> # changes = [ScenarioChange(op="replace", path="/volume", value=1000)]
    """
    changes: list[ScenarioChange] = []

    # Handle type changes
    if type(original) != type(modified):
        changes.append(ScenarioChange(
            op=ChangeOperation.REPLACE,
            path=path or "/",
            value=modified,
            previous_value=original
        ))
        return changes

    # Handle dictionaries
    if isinstance(original, dict):
        all_keys = set(original.keys()) | set(modified.keys())

        for key in all_keys:
            key_path = f"{path}/{key}"

            if key not in original:
                # Key was added
                changes.append(ScenarioChange(
                    op=ChangeOperation.ADD,
                    path=key_path,
                    value=modified[key]
                ))
            elif key not in modified:
                # Key was removed
                changes.append(ScenarioChange(
                    op=ChangeOperation.REMOVE,
                    path=key_path,
                    previous_value=original[key]
                ))
            else:
                # Key exists in both - recurse
                changes.extend(compute_diff(
                    original[key],
                    modified[key],
                    key_path
                ))

    # Handle lists
    elif isinstance(original, list):
        # Simple approach: if lists differ, generate individual changes
        max_len = max(len(original), len(modified))

        for i in range(max_len):
            item_path = f"{path}/{i}"

            if i >= len(original):
                # Item was added
                changes.append(ScenarioChange(
                    op=ChangeOperation.ADD,
                    path=item_path,
                    value=modified[i]
                ))
            elif i >= len(modified):
                # Item was removed (handle from end to preserve indices)
                changes.append(ScenarioChange(
                    op=ChangeOperation.REMOVE,
                    path=item_path,
                    previous_value=original[i]
                ))
            else:
                # Item exists in both - recurse
                changes.extend(compute_diff(
                    original[i],
                    modified[i],
                    item_path
                ))

    # Handle primitives
    else:
        if original != modified:
            changes.append(ScenarioChange(
                op=ChangeOperation.REPLACE,
                path=path,
                value=modified,
                previous_value=original
            ))

    return changes


def create_scenario_changeset(
    name: str,
    description: str = "",
    scenario_id: str | None = None
) -> ScenarioChangeSet:
    """
    Create a new empty changeset with metadata.

    Convenience factory function for creating changesets.

    Args:
        name: Human-readable scenario name
        description: Description of the scenario
        scenario_id: Optional unique identifier

    Returns:
        Empty ScenarioChangeSet ready for changes

    Example:
        >>> changeset = create_scenario_changeset(
        ...     name="Build-out 2030",
        ...     description="Projected volumes for year 2030"
        ... )
        >>> changeset.add_change(ChangeOperation.MODIFY_VOLUME, "/volume", 1500)
    """
    return ScenarioChangeSet(
        scenario_id=scenario_id,
        name=name,
        description=description,
        changes=[]
    )
