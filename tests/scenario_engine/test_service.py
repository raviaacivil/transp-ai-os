"""Tests for scenario versioning service."""

import pytest
from src.scenario_engine import (
    apply_changes,
    validate_changes,
    compute_diff,
    ScenarioChange,
    ScenarioChangeSet,
    ChangeOperation,
)
from src.scenario_engine.service import create_scenario_changeset


class TestValidateChanges:
    """Tests for changeset validation."""

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

    def test_valid_changeset(self, intersection):
        """Valid changeset should return no errors."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(op=ChangeOperation.REPLACE, path="/volume", value=1000)
        ])
        errors = validate_changes(intersection, changeset)
        assert errors == []

    def test_invalid_path(self, intersection):
        """Invalid path should return error."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.REPLACE,
                path="/nonexistent",
                value=100
            )
        ])
        errors = validate_changes(intersection, changeset)
        assert len(errors) == 1
        assert "does not exist" in errors[0].message

    def test_missing_value(self, intersection):
        """Missing required value should return error."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(op=ChangeOperation.REPLACE, path="/volume")
        ])
        errors = validate_changes(intersection, changeset)
        assert len(errors) == 1
        assert "requires a value" in errors[0].message

    def test_invalid_lanes_value(self, intersection):
        """Invalid lane count should return error."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_LANES,
                path="/lane_groups/0",
                value=0
            )
        ])
        errors = validate_changes(intersection, changeset)
        assert len(errors) == 1
        assert "positive integer" in errors[0].message

    def test_lanes_exceeds_max(self, intersection):
        """Lane count > 8 should return error."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_LANES,
                path="/lane_groups/0",
                value=10
            )
        ])
        errors = validate_changes(intersection, changeset)
        assert len(errors) == 1
        assert "cannot exceed 8" in errors[0].message

    def test_negative_volume(self, intersection):
        """Negative volume should return error."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value=-100
            )
        ])
        errors = validate_changes(intersection, changeset)
        assert len(errors) == 1
        assert "cannot be negative" in errors[0].message

    def test_invalid_timing(self, intersection):
        """Invalid timing value should return error."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_TIMING,
                path="/signal_timing",
                value={"cycle_length": -10}
            )
        ])
        errors = validate_changes(intersection, changeset)
        assert len(errors) == 1


class TestApplyChanges:
    """Tests for applying changesets."""

    @pytest.fixture
    def intersection(self):
        return {
            "volume": 800,
            "lane_groups": [
                {"num_lanes": 2, "movement_type": "through"},
                {"num_lanes": 1, "movement_type": "left"}
            ],
            "signal_timing": {
                "cycle_length": 90,
                "effective_green": 40
            }
        }

    def test_apply_single_change(self, intersection):
        """Apply a single change."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value=1200
            )
        ])

        result = apply_changes(intersection, changeset)

        assert result.success is True
        assert result.changes_applied == 1
        assert result.modified_object["volume"] == 1200

    def test_apply_multiple_changes(self, intersection):
        """Apply multiple changes in order."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value=1200
            ),
            ScenarioChange(
                op=ChangeOperation.MODIFY_LANES,
                path="/lane_groups/0",
                value=3
            ),
            ScenarioChange(
                op=ChangeOperation.MODIFY_TIMING,
                path="/signal_timing",
                value={"cycle_length": 120}
            )
        ])

        result = apply_changes(intersection, changeset)

        assert result.success is True
        assert result.changes_applied == 3
        assert result.modified_object["volume"] == 1200
        assert result.modified_object["lane_groups"][0]["num_lanes"] == 3
        assert result.modified_object["signal_timing"]["cycle_length"] == 120

    def test_original_unchanged(self, intersection):
        """Original object should not be modified."""
        original_volume = intersection["volume"]

        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value=1200
            )
        ])

        apply_changes(intersection, changeset)

        assert intersection["volume"] == original_volume

    def test_records_previous_values(self, intersection):
        """Applied changes should record previous values."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value=1200
            )
        ])

        result = apply_changes(intersection, changeset)

        assert len(result.applied_changes) == 1
        assert result.applied_changes[0].previous_value == 800
        assert result.applied_changes[0].value == 1200

    def test_invalid_changeset_rejected(self, intersection):
        """Invalid changeset should be rejected entirely."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value=1200
            ),
            ScenarioChange(
                op=ChangeOperation.REPLACE,
                path="/nonexistent",
                value=100
            )
        ])

        result = apply_changes(intersection, changeset)

        assert result.success is False
        assert result.modified_object is None
        assert len(result.errors) > 0

    def test_skip_validation(self, intersection):
        """Can skip validation if needed."""
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value=1200
            )
        ])

        result = apply_changes(intersection, changeset, validate=False)

        assert result.success is True


class TestComputeDiff:
    """Tests for computing differences between objects."""

    def test_no_changes(self):
        """Identical objects should have no diff."""
        obj = {"volume": 800}
        changes = compute_diff(obj, obj.copy())
        assert changes == []

    def test_simple_value_change(self):
        """Detect simple value change."""
        original = {"volume": 800}
        modified = {"volume": 1200}

        changes = compute_diff(original, modified)

        assert len(changes) == 1
        assert changes[0].op == ChangeOperation.REPLACE
        assert changes[0].path == "/volume"
        assert changes[0].value == 1200
        assert changes[0].previous_value == 800

    def test_nested_change(self):
        """Detect nested value change."""
        original = {"timing": {"cycle": 90}}
        modified = {"timing": {"cycle": 120}}

        changes = compute_diff(original, modified)

        assert len(changes) == 1
        assert changes[0].path == "/timing/cycle"

    def test_added_key(self):
        """Detect added key."""
        original = {"a": 1}
        modified = {"a": 1, "b": 2}

        changes = compute_diff(original, modified)

        assert len(changes) == 1
        assert changes[0].op == ChangeOperation.ADD
        assert changes[0].path == "/b"
        assert changes[0].value == 2

    def test_removed_key(self):
        """Detect removed key."""
        original = {"a": 1, "b": 2}
        modified = {"a": 1}

        changes = compute_diff(original, modified)

        assert len(changes) == 1
        assert changes[0].op == ChangeOperation.REMOVE
        assert changes[0].path == "/b"

    def test_array_element_change(self):
        """Detect array element change."""
        original = {"items": [1, 2, 3]}
        modified = {"items": [1, 5, 3]}

        changes = compute_diff(original, modified)

        assert len(changes) == 1
        assert changes[0].path == "/items/1"
        assert changes[0].value == 5

    def test_multiple_changes(self):
        """Detect multiple changes."""
        original = {"a": 1, "b": 2}
        modified = {"a": 10, "b": 20}

        changes = compute_diff(original, modified)

        assert len(changes) == 2


class TestScenarioChangeSet:
    """Tests for ScenarioChangeSet."""

    def test_fluent_interface(self):
        """Test fluent add_change interface."""
        changeset = ScenarioChangeSet()
        changeset.add_change(
            ChangeOperation.MODIFY_VOLUME, "/volume", 1200
        ).add_change(
            ChangeOperation.ADD_LANE, "/lane_groups/0"
        )

        assert len(changeset.changes) == 2

    def test_create_scenario_changeset(self):
        """Test factory function."""
        changeset = create_scenario_changeset(
            name="Build-out 2030",
            description="Projected volumes"
        )

        assert changeset.name == "Build-out 2030"
        assert changeset.description == "Projected volumes"
        assert changeset.changes == []


class TestDeterminism:
    """Tests to verify deterministic behavior."""

    def test_same_input_same_output(self):
        """Same inputs should produce identical outputs."""
        intersection = {
            "volume": 800,
            "lane_groups": [{"num_lanes": 2}]
        }
        changeset = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value=1200
            )
        ])

        result1 = apply_changes(intersection, changeset)
        result2 = apply_changes(intersection, changeset)

        assert result1.modified_object == result2.modified_object
        assert result1.changes_applied == result2.changes_applied

    def test_order_matters(self):
        """Change order should affect final result."""
        intersection = {"volume": 800}

        changeset1 = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value="+100"
            ),
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value="*2"
            )
        ])

        changeset2 = ScenarioChangeSet(changes=[
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value="*2"
            ),
            ScenarioChange(
                op=ChangeOperation.MODIFY_VOLUME,
                path="/volume",
                value="+100"
            )
        ])

        result1 = apply_changes(intersection, changeset1)
        result2 = apply_changes(intersection, changeset2)

        # (800 + 100) * 2 = 1800
        assert result1.modified_object["volume"] == 1800
        # (800 * 2) + 100 = 1700
        assert result2.modified_object["volume"] == 1700
