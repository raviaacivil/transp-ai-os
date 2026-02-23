"""
Change operation handlers.

Each operation is implemented as a pure function that takes the current
object state and returns a new state. No mutations of the input object.
"""

from copy import deepcopy
from typing import Any

from .models import ChangeOperation, ScenarioChange


def parse_path(path: str) -> list[str]:
    """
    Parse a JSON Pointer path into segments.

    Args:
        path: JSON Pointer (e.g., "/lane_groups/0/num_lanes")

    Returns:
        List of path segments (e.g., ["lane_groups", "0", "num_lanes"])
    """
    if path == "/":
        return []
    # Remove leading slash and split
    return path[1:].split("/")


def get_value_at_path(obj: dict[str, Any], path: str) -> Any:
    """
    Get value at a JSON Pointer path.

    Args:
        obj: The object to traverse
        path: JSON Pointer path

    Returns:
        Value at the path

    Raises:
        KeyError: If path doesn't exist
        IndexError: If array index is out of bounds
    """
    segments = parse_path(path)
    current = obj

    for segment in segments:
        if isinstance(current, list):
            index = int(segment)
            current = current[index]
        elif isinstance(current, dict):
            current = current[segment]
        else:
            raise KeyError(f"Cannot traverse into {type(current)} at {segment}")

    return current


def set_value_at_path(
    obj: dict[str, Any],
    path: str,
    value: Any
) -> tuple[dict[str, Any], Any]:
    """
    Set value at a JSON Pointer path (immutable).

    Args:
        obj: The original object
        path: JSON Pointer path
        value: New value to set

    Returns:
        Tuple of (new object with value set, previous value)

    Raises:
        KeyError: If path doesn't exist
    """
    result = deepcopy(obj)
    segments = parse_path(path)

    if not segments:
        raise ValueError("Cannot replace root object")

    # Navigate to parent
    current = result
    for segment in segments[:-1]:
        if isinstance(current, list):
            current = current[int(segment)]
        else:
            current = current[segment]

    # Get previous value and set new value
    final_segment = segments[-1]
    if isinstance(current, list):
        index = int(final_segment)
        previous = current[index]
        current[index] = value
    else:
        previous = current.get(final_segment)
        current[final_segment] = value

    return result, previous


def delete_at_path(obj: dict[str, Any], path: str) -> tuple[dict[str, Any], Any]:
    """
    Delete value at a JSON Pointer path (immutable).

    Args:
        obj: The original object
        path: JSON Pointer path

    Returns:
        Tuple of (new object with value deleted, deleted value)
    """
    result = deepcopy(obj)
    segments = parse_path(path)

    if not segments:
        raise ValueError("Cannot delete root object")

    # Navigate to parent
    current = result
    for segment in segments[:-1]:
        if isinstance(current, list):
            current = current[int(segment)]
        else:
            current = current[segment]

    # Delete the value
    final_segment = segments[-1]
    if isinstance(current, list):
        index = int(final_segment)
        previous = current[index]
        del current[index]
    else:
        previous = current.pop(final_segment)

    return result, previous


def insert_at_path(
    obj: dict[str, Any],
    path: str,
    value: Any
) -> dict[str, Any]:
    """
    Insert value at a JSON Pointer path (for arrays).

    Args:
        obj: The original object
        path: JSON Pointer path (with index or "-" for append)
        value: Value to insert

    Returns:
        New object with value inserted
    """
    result = deepcopy(obj)
    segments = parse_path(path)

    if not segments:
        raise ValueError("Cannot insert at root")

    # Navigate to parent
    current = result
    for segment in segments[:-1]:
        if isinstance(current, list):
            current = current[int(segment)]
        else:
            current = current[segment]

    # Insert the value
    final_segment = segments[-1]
    if isinstance(current, list):
        if final_segment == "-":
            current.append(value)
        else:
            current.insert(int(final_segment), value)
    else:
        current[final_segment] = value

    return result


# --- Operation Handlers ---

def apply_replace(
    obj: dict[str, Any],
    change: ScenarioChange
) -> tuple[dict[str, Any], Any]:
    """Apply a replace operation."""
    return set_value_at_path(obj, change.path, change.value)


def apply_add(
    obj: dict[str, Any],
    change: ScenarioChange
) -> tuple[dict[str, Any], Any]:
    """Apply an add operation."""
    result = insert_at_path(obj, change.path, change.value)
    return result, None


def apply_remove(
    obj: dict[str, Any],
    change: ScenarioChange
) -> tuple[dict[str, Any], Any]:
    """Apply a remove operation."""
    return delete_at_path(obj, change.path)


def apply_add_lane(
    obj: dict[str, Any],
    change: ScenarioChange
) -> tuple[dict[str, Any], Any]:
    """
    Add a lane to a lane group.

    Path should point to a lane group (e.g., "/lane_groups/0").
    Increments num_lanes by 1.
    """
    result = deepcopy(obj)
    lane_group = get_value_at_path(result, change.path)

    previous = lane_group.get("num_lanes", 1)
    lane_group["num_lanes"] = previous + 1

    return result, previous


def apply_remove_lane(
    obj: dict[str, Any],
    change: ScenarioChange
) -> tuple[dict[str, Any], Any]:
    """
    Remove a lane from a lane group.

    Path should point to a lane group.
    Decrements num_lanes by 1 (minimum 1).
    """
    result = deepcopy(obj)
    lane_group = get_value_at_path(result, change.path)

    previous = lane_group.get("num_lanes", 1)
    new_value = max(1, previous - 1)
    lane_group["num_lanes"] = new_value

    return result, previous


def apply_modify_lanes(
    obj: dict[str, Any],
    change: ScenarioChange
) -> tuple[dict[str, Any], Any]:
    """
    Set the number of lanes for a lane group.

    Path should point to a lane group.
    Value should be the new number of lanes.
    """
    result = deepcopy(obj)
    lane_group = get_value_at_path(result, change.path)

    previous = lane_group.get("num_lanes", 1)
    lane_group["num_lanes"] = change.value

    return result, previous


def apply_modify_volume(
    obj: dict[str, Any],
    change: ScenarioChange
) -> tuple[dict[str, Any], Any]:
    """
    Modify volume at a path.

    Supports both absolute values and relative changes:
        - value: 1200 -> Set volume to 1200
        - value: "+100" -> Increase volume by 100
        - value: "-50" -> Decrease volume by 50
        - value: "*1.1" -> Multiply volume by 1.1
    """
    result = deepcopy(obj)
    segments = parse_path(change.path)

    # Navigate to the target
    current = result
    for segment in segments[:-1]:
        if isinstance(current, list):
            current = current[int(segment)]
        else:
            current = current[segment]

    # Get the volume key (last segment or "volume" if path points to object)
    final_segment = segments[-1] if segments else "volume"

    if isinstance(current, dict) and final_segment not in current:
        # Path points to an object, modify its "volume" key
        final_segment = "volume"

    previous = current.get(final_segment, 0)
    value = change.value

    # Handle relative changes
    if isinstance(value, str):
        if value.startswith("+"):
            new_value = previous + float(value[1:])
        elif value.startswith("-"):
            new_value = previous - float(value[1:])
        elif value.startswith("*"):
            new_value = previous * float(value[1:])
        else:
            new_value = float(value)
    else:
        new_value = value

    # Ensure non-negative
    current[final_segment] = max(0, new_value)

    return result, previous


def apply_modify_timing(
    obj: dict[str, Any],
    change: ScenarioChange
) -> tuple[dict[str, Any], Any]:
    """
    Modify signal timing parameters.

    Path should point to signal_timing object.
    Value should be a dict with timing parameters to update.
    """
    result = deepcopy(obj)
    timing = get_value_at_path(result, change.path)

    previous = deepcopy(timing)

    # Update timing parameters
    if isinstance(change.value, dict):
        timing.update(change.value)

    return result, previous


# --- Operation Dispatcher ---

OPERATION_HANDLERS = {
    ChangeOperation.REPLACE: apply_replace,
    ChangeOperation.ADD: apply_add,
    ChangeOperation.REMOVE: apply_remove,
    ChangeOperation.ADD_LANE: apply_add_lane,
    ChangeOperation.REMOVE_LANE: apply_remove_lane,
    ChangeOperation.MODIFY_LANES: apply_modify_lanes,
    ChangeOperation.MODIFY_VOLUME: apply_modify_volume,
    ChangeOperation.MODIFY_TIMING: apply_modify_timing,
}


def apply_operation(
    obj: dict[str, Any],
    change: ScenarioChange
) -> tuple[dict[str, Any], Any]:
    """
    Apply a single change operation.

    Args:
        obj: Current object state
        change: Change to apply

    Returns:
        Tuple of (new object state, previous value)

    Raises:
        ValueError: If operation is not supported
    """
    handler = OPERATION_HANDLERS.get(change.op)
    if handler is None:
        raise ValueError(f"Unsupported operation: {change.op}")

    return handler(obj, change)
