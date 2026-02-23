"""Tests for scenario change operations."""

import pytest
from src.scenario_engine.operations import (
    parse_path,
    get_value_at_path,
    set_value_at_path,
    delete_at_path,
    insert_at_path,
    apply_operation,
)
from src.scenario_engine.models import ChangeOperation, ScenarioChange


class TestParsePath:
    """Tests for JSON Pointer path parsing."""

    def test_simple_path(self):
        """Parse simple single-segment path."""
        assert parse_path("/volume") == ["volume"]

    def test_nested_path(self):
        """Parse nested path."""
        assert parse_path("/lane_groups/0/num_lanes") == [
            "lane_groups", "0", "num_lanes"
        ]

    def test_root_path(self):
        """Parse root path."""
        assert parse_path("/") == []


class TestGetValueAtPath:
    """Tests for getting values at paths."""

    @pytest.fixture
    def sample_obj(self):
        return {
            "volume": 800,
            "num_lanes": 2,
            "lane_groups": [
                {"num_lanes": 1, "movement_type": "left"},
                {"num_lanes": 2, "movement_type": "through"},
            ],
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

    def test_get_simple_value(self, sample_obj):
        """Get a top-level value."""
        assert get_value_at_path(sample_obj, "/volume") == 800

    def test_get_nested_value(self, sample_obj):
        """Get a nested value."""
        assert get_value_at_path(sample_obj, "/signal_timing/cycle_length") == 90

    def test_get_array_element(self, sample_obj):
        """Get an array element."""
        assert get_value_at_path(sample_obj, "/lane_groups/0") == {
            "num_lanes": 1, "movement_type": "left"
        }

    def test_get_nested_array_value(self, sample_obj):
        """Get a value inside an array element."""
        assert get_value_at_path(sample_obj, "/lane_groups/1/num_lanes") == 2

    def test_nonexistent_path_raises(self, sample_obj):
        """Nonexistent path raises KeyError."""
        with pytest.raises(KeyError):
            get_value_at_path(sample_obj, "/nonexistent")

    def test_invalid_index_raises(self, sample_obj):
        """Invalid array index raises IndexError."""
        with pytest.raises(IndexError):
            get_value_at_path(sample_obj, "/lane_groups/99")


class TestSetValueAtPath:
    """Tests for setting values at paths."""

    @pytest.fixture
    def sample_obj(self):
        return {
            "volume": 800,
            "lane_groups": [
                {"num_lanes": 2}
            ]
        }

    def test_set_simple_value(self, sample_obj):
        """Set a top-level value."""
        result, previous = set_value_at_path(sample_obj, "/volume", 1200)
        assert result["volume"] == 1200
        assert previous == 800

    def test_set_nested_value(self, sample_obj):
        """Set a nested value."""
        result, previous = set_value_at_path(
            sample_obj, "/lane_groups/0/num_lanes", 3
        )
        assert result["lane_groups"][0]["num_lanes"] == 3
        assert previous == 2

    def test_original_unchanged(self, sample_obj):
        """Original object should be unchanged."""
        set_value_at_path(sample_obj, "/volume", 1200)
        assert sample_obj["volume"] == 800  # Original unchanged


class TestDeleteAtPath:
    """Tests for deleting values at paths."""

    def test_delete_key(self):
        """Delete a dictionary key."""
        obj = {"a": 1, "b": 2}
        result, previous = delete_at_path(obj, "/a")
        assert "a" not in result
        assert "b" in result
        assert previous == 1

    def test_delete_array_element(self):
        """Delete an array element."""
        obj = {"items": [1, 2, 3]}
        result, previous = delete_at_path(obj, "/items/1")
        assert result["items"] == [1, 3]
        assert previous == 2


class TestInsertAtPath:
    """Tests for inserting values at paths."""

    def test_insert_at_index(self):
        """Insert at a specific array index."""
        obj = {"items": [1, 3]}
        result = insert_at_path(obj, "/items/1", 2)
        assert result["items"] == [1, 2, 3]

    def test_append_with_dash(self):
        """Append to array using '-'."""
        obj = {"items": [1, 2]}
        result = insert_at_path(obj, "/items/-", 3)
        assert result["items"] == [1, 2, 3]

    def test_insert_new_key(self):
        """Insert a new dictionary key."""
        obj = {"a": 1}
        result = insert_at_path(obj, "/b", 2)
        assert result == {"a": 1, "b": 2}


class TestApplyOperation:
    """Tests for the operation dispatcher."""

    @pytest.fixture
    def intersection(self):
        return {
            "volume": 800,
            "lane_groups": [
                {"num_lanes": 2, "movement_type": "through"}
            ],
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

    def test_replace_operation(self, intersection):
        """Apply replace operation."""
        change = ScenarioChange(
            op=ChangeOperation.REPLACE,
            path="/volume",
            value=1200
        )
        result, previous = apply_operation(intersection, change)
        assert result["volume"] == 1200
        assert previous == 800

    def test_add_lane_operation(self, intersection):
        """Apply add_lane operation."""
        change = ScenarioChange(
            op=ChangeOperation.ADD_LANE,
            path="/lane_groups/0"
        )
        result, previous = apply_operation(intersection, change)
        assert result["lane_groups"][0]["num_lanes"] == 3
        assert previous == 2

    def test_remove_lane_operation(self, intersection):
        """Apply remove_lane operation."""
        change = ScenarioChange(
            op=ChangeOperation.REMOVE_LANE,
            path="/lane_groups/0"
        )
        result, previous = apply_operation(intersection, change)
        assert result["lane_groups"][0]["num_lanes"] == 1
        assert previous == 2

    def test_remove_lane_minimum(self, intersection):
        """Remove lane should not go below 1."""
        intersection["lane_groups"][0]["num_lanes"] = 1
        change = ScenarioChange(
            op=ChangeOperation.REMOVE_LANE,
            path="/lane_groups/0"
        )
        result, _ = apply_operation(intersection, change)
        assert result["lane_groups"][0]["num_lanes"] == 1

    def test_modify_lanes_operation(self, intersection):
        """Apply modify_lanes operation."""
        change = ScenarioChange(
            op=ChangeOperation.MODIFY_LANES,
            path="/lane_groups/0",
            value=4
        )
        result, previous = apply_operation(intersection, change)
        assert result["lane_groups"][0]["num_lanes"] == 4
        assert previous == 2

    def test_modify_volume_absolute(self, intersection):
        """Modify volume with absolute value."""
        change = ScenarioChange(
            op=ChangeOperation.MODIFY_VOLUME,
            path="/volume",
            value=1500
        )
        result, previous = apply_operation(intersection, change)
        assert result["volume"] == 1500
        assert previous == 800

    def test_modify_volume_increase(self, intersection):
        """Modify volume with relative increase."""
        change = ScenarioChange(
            op=ChangeOperation.MODIFY_VOLUME,
            path="/volume",
            value="+200"
        )
        result, previous = apply_operation(intersection, change)
        assert result["volume"] == 1000
        assert previous == 800

    def test_modify_volume_decrease(self, intersection):
        """Modify volume with relative decrease."""
        change = ScenarioChange(
            op=ChangeOperation.MODIFY_VOLUME,
            path="/volume",
            value="-100"
        )
        result, _ = apply_operation(intersection, change)
        assert result["volume"] == 700

    def test_modify_volume_multiply(self, intersection):
        """Modify volume with multiplier."""
        change = ScenarioChange(
            op=ChangeOperation.MODIFY_VOLUME,
            path="/volume",
            value="*1.5"
        )
        result, _ = apply_operation(intersection, change)
        assert result["volume"] == 1200

    def test_modify_volume_no_negative(self, intersection):
        """Volume should not go negative."""
        change = ScenarioChange(
            op=ChangeOperation.MODIFY_VOLUME,
            path="/volume",
            value="-1000"
        )
        result, _ = apply_operation(intersection, change)
        assert result["volume"] == 0

    def test_modify_timing_operation(self, intersection):
        """Apply modify_timing operation."""
        change = ScenarioChange(
            op=ChangeOperation.MODIFY_TIMING,
            path="/signal_timing",
            value={"cycle_length": 120, "effective_green": 50}
        )
        result, previous = apply_operation(intersection, change)
        assert result["signal_timing"]["cycle_length"] == 120
        assert result["signal_timing"]["effective_green"] == 50
        assert previous["cycle_length"] == 90
