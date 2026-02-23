"""
Validation logic for scenario changes.

Validates changes before they are applied to ensure
data integrity and catch errors early.
"""

from typing import Any

from .models import ChangeOperation, ScenarioChange, ValidationError
from .operations import parse_path, get_value_at_path


def validate_path_exists(
    obj: dict[str, Any],
    path: str,
    change_index: int
) -> ValidationError | None:
    """
    Validate that a path exists in the object.

    Args:
        obj: The object to check
        path: JSON Pointer path
        change_index: Index of the change (for error reporting)

    Returns:
        ValidationError if path doesn't exist, None otherwise
    """
    try:
        get_value_at_path(obj, path)
        return None
    except (KeyError, IndexError, TypeError) as e:
        return ValidationError(
            path=path,
            message=f"Path does not exist: {e}",
            change_index=change_index
        )


def validate_parent_exists(
    obj: dict[str, Any],
    path: str,
    change_index: int
) -> ValidationError | None:
    """
    Validate that the parent of a path exists (for add operations).

    Args:
        obj: The object to check
        path: JSON Pointer path
        change_index: Index of the change

    Returns:
        ValidationError if parent doesn't exist, None otherwise
    """
    segments = parse_path(path)
    if len(segments) <= 1:
        return None

    parent_path = "/" + "/".join(segments[:-1])
    try:
        get_value_at_path(obj, parent_path)
        return None
    except (KeyError, IndexError, TypeError) as e:
        return ValidationError(
            path=path,
            message=f"Parent path does not exist: {e}",
            change_index=change_index
        )


def validate_value_required(
    change: ScenarioChange,
    change_index: int
) -> ValidationError | None:
    """
    Validate that a value is provided for operations that require it.

    Args:
        change: The change to validate
        change_index: Index of the change

    Returns:
        ValidationError if value is missing, None otherwise
    """
    requires_value = {
        ChangeOperation.REPLACE,
        ChangeOperation.ADD,
        ChangeOperation.MODIFY_LANES,
        ChangeOperation.MODIFY_VOLUME,
        ChangeOperation.MODIFY_TIMING,
    }

    if change.op in requires_value and change.value is None:
        return ValidationError(
            path=change.path,
            message=f"Operation '{change.op.value}' requires a value",
            change_index=change_index
        )

    return None


def validate_lanes_value(
    change: ScenarioChange,
    change_index: int
) -> ValidationError | None:
    """
    Validate lane count value.

    Args:
        change: The change to validate
        change_index: Index of the change

    Returns:
        ValidationError if invalid, None otherwise
    """
    if change.op != ChangeOperation.MODIFY_LANES:
        return None

    if not isinstance(change.value, int) or change.value < 1:
        return ValidationError(
            path=change.path,
            message="Number of lanes must be a positive integer",
            change_index=change_index
        )

    if change.value > 8:
        return ValidationError(
            path=change.path,
            message="Number of lanes cannot exceed 8",
            change_index=change_index
        )

    return None


def validate_volume_value(
    change: ScenarioChange,
    change_index: int
) -> ValidationError | None:
    """
    Validate volume value.

    Args:
        change: The change to validate
        change_index: Index of the change

    Returns:
        ValidationError if invalid, None otherwise
    """
    if change.op != ChangeOperation.MODIFY_VOLUME:
        return None

    value = change.value

    # Allow relative values as strings
    if isinstance(value, str):
        if value[0] in "+-*":
            try:
                float(value[1:])
                return None
            except ValueError:
                return ValidationError(
                    path=change.path,
                    message=f"Invalid relative volume value: {value}",
                    change_index=change_index
                )
        else:
            try:
                float(value)
                return None
            except ValueError:
                return ValidationError(
                    path=change.path,
                    message=f"Invalid volume value: {value}",
                    change_index=change_index
                )

    # Absolute values must be non-negative numbers
    if not isinstance(value, (int, float)):
        return ValidationError(
            path=change.path,
            message="Volume must be a number or relative string",
            change_index=change_index
        )

    if value < 0:
        return ValidationError(
            path=change.path,
            message="Volume cannot be negative",
            change_index=change_index
        )

    return None


def validate_timing_value(
    change: ScenarioChange,
    change_index: int
) -> ValidationError | None:
    """
    Validate timing modification value.

    Args:
        change: The change to validate
        change_index: Index of the change

    Returns:
        ValidationError if invalid, None otherwise
    """
    if change.op != ChangeOperation.MODIFY_TIMING:
        return None

    if not isinstance(change.value, dict):
        return ValidationError(
            path=change.path,
            message="Timing value must be a dictionary",
            change_index=change_index
        )

    # Validate individual timing parameters
    if "cycle_length" in change.value:
        cl = change.value["cycle_length"]
        if not isinstance(cl, (int, float)) or cl <= 0 or cl > 300:
            return ValidationError(
                path=change.path,
                message="cycle_length must be between 0 and 300",
                change_index=change_index
            )

    if "effective_green" in change.value:
        eg = change.value["effective_green"]
        if not isinstance(eg, (int, float)) or eg <= 0:
            return ValidationError(
                path=change.path,
                message="effective_green must be positive",
                change_index=change_index
            )

    return None


def validate_change(
    obj: dict[str, Any],
    change: ScenarioChange,
    change_index: int
) -> list[ValidationError]:
    """
    Validate a single change against the current object state.

    Args:
        obj: Current object state
        change: Change to validate
        change_index: Index of the change

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[ValidationError] = []

    # Value required check
    err = validate_value_required(change, change_index)
    if err:
        errors.append(err)

    # Path existence checks
    if change.op in {
        ChangeOperation.REPLACE,
        ChangeOperation.REMOVE,
        ChangeOperation.ADD_LANE,
        ChangeOperation.REMOVE_LANE,
        ChangeOperation.MODIFY_LANES,
        ChangeOperation.MODIFY_TIMING,
    }:
        err = validate_path_exists(obj, change.path, change_index)
        if err:
            errors.append(err)

    if change.op == ChangeOperation.ADD:
        err = validate_parent_exists(obj, change.path, change_index)
        if err:
            errors.append(err)

    # Domain-specific validation
    err = validate_lanes_value(change, change_index)
    if err:
        errors.append(err)

    err = validate_volume_value(change, change_index)
    if err:
        errors.append(err)

    err = validate_timing_value(change, change_index)
    if err:
        errors.append(err)

    return errors
