"""Tests for report narrative generator."""

import pytest
from src.report_generator import (
    generate_narrative,
    IntersectionResult,
    ScenarioResult,
    ScenarioComparison,
    LaneGroupResult,
)
from src.report_generator.models import LOS, AnalysisPeriod, ScenarioType


@pytest.fixture
def sample_intersection():
    """Sample intersection result."""
    return IntersectionResult(
        name="Main St & 1st Ave",
        control_type="Signalized",
        analysis_period=AnalysisPeriod.PM_PEAK,
        overall_los=LOS.C,
        overall_delay=28.5,
        overall_vc=0.85,
        worst_approach_los=LOS.D,
        worst_approach_name="Eastbound",
        worst_movement_los=LOS.D,
        worst_movement_name="EBL",
        cycle_length=90,
        lane_groups=[
            LaneGroupResult(
                name="EBL",
                movement="Eastbound Left",
                volume=150,
                capacity=200,
                vc_ratio=0.75,
                delay=42.3,
                los=LOS.D,
                queue_95th=125
            ),
            LaneGroupResult(
                name="EBT",
                movement="Eastbound Through",
                volume=800,
                capacity=1200,
                vc_ratio=0.67,
                delay=22.1,
                los=LOS.C,
                queue_95th=200
            )
        ]
    )


@pytest.fixture
def sample_scenario(sample_intersection):
    """Sample scenario result."""
    return ScenarioResult(
        scenario_type=ScenarioType.EXISTING,
        scenario_name="Existing Conditions",
        year=2024,
        intersections=[sample_intersection]
    )


@pytest.fixture
def sample_comparison(sample_intersection):
    """Sample scenario comparison."""
    baseline_int = sample_intersection.model_copy()

    proposed_int = sample_intersection.model_copy()
    proposed_int.overall_los = LOS.D
    proposed_int.overall_delay = 38.2
    proposed_int.overall_vc = 0.92

    baseline = ScenarioResult(
        scenario_type=ScenarioType.EXISTING,
        scenario_name="Existing Conditions",
        year=2024,
        intersections=[baseline_int]
    )

    proposed = ScenarioResult(
        scenario_type=ScenarioType.BUILD,
        scenario_name="With Project",
        year=2024,
        intersections=[proposed_int]
    )

    return ScenarioComparison(
        baseline=baseline,
        proposed=proposed,
        project_name="Proposed Mixed-Use Development",
        project_trips_am=150,
        project_trips_pm=200
    )


class TestSingleIntersectionNarrative:
    """Tests for single intersection narrative generation."""

    def test_generates_sections(self, sample_intersection):
        """Should generate narrative sections."""
        result = generate_narrative(intersection=sample_intersection)

        assert len(result.sections) >= 1
        assert result.generated_from == "IntersectionResult"
        assert result.data_hash is not None

    def test_includes_intersection_name(self, sample_intersection):
        """Narrative should include intersection name."""
        result = generate_narrative(intersection=sample_intersection)

        content = result.sections[0].content
        assert "Main St & 1st Ave" in content

    def test_includes_los(self, sample_intersection):
        """Narrative should include LOS."""
        result = generate_narrative(intersection=sample_intersection)

        content = result.sections[0].content
        assert "LOS C" in content

    def test_includes_delay(self, sample_intersection):
        """Narrative should include delay."""
        result = generate_narrative(intersection=sample_intersection)

        content = result.sections[0].content
        assert "28.5" in content
        assert "delay" in content.lower()

    def test_includes_vc_ratio(self, sample_intersection):
        """Narrative should include v/c ratio."""
        result = generate_narrative(intersection=sample_intersection)

        content = result.sections[0].content
        assert "0.85" in content

    def test_includes_worst_approach(self, sample_intersection):
        """Narrative should include worst approach."""
        result = generate_narrative(intersection=sample_intersection)

        content = result.sections[0].content
        assert "Eastbound" in content

    def test_lane_group_details(self, sample_intersection):
        """Should include lane group details when requested."""
        result = generate_narrative(
            intersection=sample_intersection,
            include_lane_groups=True
        )

        assert len(result.sections) == 2
        lg_section = result.sections[1]
        assert "EBL" in lg_section.content
        assert "EBT" in lg_section.content


class TestScenarioNarrative:
    """Tests for scenario narrative generation."""

    def test_generates_sections(self, sample_scenario):
        """Should generate narrative sections."""
        result = generate_narrative(scenario=sample_scenario)

        assert len(result.sections) >= 2  # Intro + intersection
        assert result.generated_from == "ScenarioResult"

    def test_includes_scenario_name(self, sample_scenario):
        """Narrative should include scenario name."""
        result = generate_narrative(scenario=sample_scenario)

        intro = result.sections[0].content
        assert "Existing Conditions" in intro

    def test_includes_year(self, sample_scenario):
        """Narrative should include analysis year."""
        result = generate_narrative(scenario=sample_scenario)

        intro = result.sections[0].content
        assert "2024" in intro

    def test_includes_intersection_count(self, sample_scenario):
        """Narrative should include intersection count."""
        result = generate_narrative(scenario=sample_scenario)

        intro = result.sections[0].content
        assert "1 intersection" in intro


class TestComparisonNarrative:
    """Tests for scenario comparison narrative generation."""

    def test_generates_all_sections(self, sample_comparison):
        """Should generate all required sections."""
        result = generate_narrative(comparison=sample_comparison)

        section_ids = [s.section_id for s in result.sections]
        assert "executive_summary" in section_ids
        assert "compliance_statement" in section_ids
        assert result.generated_from == "ScenarioComparison"

    def test_executive_summary_content(self, sample_comparison):
        """Executive summary should include key information."""
        result = generate_narrative(comparison=sample_comparison)

        exec_summary = next(
            s for s in result.sections if s.section_id == "executive_summary"
        )
        content = exec_summary.content

        assert "Proposed Mixed-Use Development" in content
        assert "150" in content  # AM trips
        assert "200" in content  # PM trips
        assert "Existing Conditions" in content
        assert "With Project" in content

    def test_comparison_paragraph(self, sample_comparison):
        """Should generate comparison paragraph."""
        result = generate_narrative(comparison=sample_comparison)

        comparison_sections = [
            s for s in result.sections if "comparison" in s.section_id.lower()
        ]
        assert len(comparison_sections) >= 1

        content = comparison_sections[0].content
        assert "LOS" in content
        assert "changed" in content.lower() or "remained" in content.lower()

    def test_delay_change_reported(self, sample_comparison):
        """Comparison should report delay change."""
        result = generate_narrative(comparison=sample_comparison)

        comparison_section = next(
            s for s in result.sections
            if "comparison_main" in s.section_id.lower()
        )
        content = comparison_section.content

        # Should mention both delay values
        assert "28.5" in content
        assert "38.2" in content


class TestComplianceStatement:
    """Tests for compliance statement generation."""

    def test_no_thresholds_provided(self, sample_comparison):
        """Should indicate when no thresholds provided."""
        result = generate_narrative(comparison=sample_comparison)

        compliance = next(
            s for s in result.sections if s.section_id == "compliance_statement"
        )

        assert "No specific LOS" in compliance.content
        assert "thresholds were provided" in compliance.content

    def test_with_los_threshold(self, sample_comparison):
        """Should check against provided LOS threshold."""
        result = generate_narrative(
            comparison=sample_comparison,
            threshold_los=LOS.C
        )

        compliance = next(
            s for s in result.sections if s.section_id == "compliance_statement"
        )

        # Proposed is LOS D, threshold is C, should fail
        assert "does not meet" in compliance.content
        assert "LOS D" in compliance.content
        assert "LOS C" in compliance.content

    def test_with_vc_threshold(self, sample_comparison):
        """Should check against provided v/c threshold."""
        result = generate_narrative(
            comparison=sample_comparison,
            threshold_vc=0.90
        )

        compliance = next(
            s for s in result.sections if s.section_id == "compliance_statement"
        )

        # Proposed has v/c of 0.92, threshold is 0.90, should fail
        assert "does not meet" in compliance.content
        assert "0.92" in compliance.content

    def test_passing_thresholds(self, sample_comparison):
        """Should indicate compliance when thresholds are met."""
        result = generate_narrative(
            comparison=sample_comparison,
            threshold_los=LOS.E,  # Lenient threshold
            threshold_vc=1.0
        )

        compliance = next(
            s for s in result.sections if s.section_id == "compliance_statement"
        )

        assert "meets" in compliance.content

    def test_jurisdiction_included(self, sample_comparison):
        """Should include jurisdiction when provided."""
        result = generate_narrative(
            comparison=sample_comparison,
            threshold_los=LOS.D,
            jurisdiction="City of Example"
        )

        compliance = next(
            s for s in result.sections if s.section_id == "compliance_statement"
        )

        assert "City of Example" in compliance.content


class TestDataIntegrity:
    """Tests to ensure no data hallucination."""

    def test_only_uses_provided_data(self, sample_intersection):
        """Narrative should only contain data from input."""
        result = generate_narrative(intersection=sample_intersection)

        content = result.sections[0].content

        # Should contain provided values
        assert "28.5" in content  # Actual delay
        assert "C" in content      # Actual LOS

        # Should NOT contain made-up values
        assert "acceptable" not in content.lower()
        assert "significant" not in content.lower()
        assert "policy" not in content.lower()
        assert "standard" not in content.lower()

    def test_no_hallucinated_thresholds(self, sample_comparison):
        """Should not reference thresholds unless provided."""
        result = generate_narrative(comparison=sample_comparison)

        all_content = " ".join(s.content for s in result.sections)

        # Should NOT contain assumed standards
        assert "LOS D or better" not in all_content
        assert "agency standard" not in all_content
        assert "municipal code" not in all_content
        assert "general plan" not in all_content

    def test_hash_changes_with_data(self, sample_intersection):
        """Data hash should change when input changes."""
        result1 = generate_narrative(intersection=sample_intersection)

        modified = sample_intersection.model_copy()
        modified.overall_delay = 35.0

        result2 = generate_narrative(intersection=modified)

        assert result1.data_hash != result2.data_hash


class TestOutputStructure:
    """Tests for output structure validation."""

    def test_sections_have_required_fields(self, sample_intersection):
        """Each section should have required fields."""
        result = generate_narrative(intersection=sample_intersection)

        for section in result.sections:
            assert section.section_id is not None
            assert section.title is not None
            assert section.content is not None
            assert len(section.content) > 0

    def test_section_ids_unique(self, sample_comparison):
        """Section IDs should be unique."""
        result = generate_narrative(comparison=sample_comparison)

        ids = [s.section_id for s in result.sections]
        assert len(ids) == len(set(ids))

    def test_requires_input(self):
        """Should raise error if no input provided."""
        with pytest.raises(ValueError):
            generate_narrative()


class TestEdgeCases:
    """Tests for edge cases."""

    def test_intersection_without_optional_fields(self):
        """Should handle intersection without optional fields."""
        minimal = IntersectionResult(
            name="Simple Intersection",
            analysis_period=AnalysisPeriod.AM_PEAK,
            overall_los=LOS.B,
            overall_delay=15.0
        )

        result = generate_narrative(intersection=minimal)
        assert len(result.sections) >= 1
        assert "Simple Intersection" in result.sections[0].content

    def test_los_f_intersection(self):
        """Should handle failing intersection."""
        failing = IntersectionResult(
            name="Failing Intersection",
            analysis_period=AnalysisPeriod.PM_PEAK,
            overall_los=LOS.F,
            overall_delay=120.5,
            overall_vc=1.25
        )

        result = generate_narrative(intersection=failing)
        content = result.sections[0].content

        assert "LOS F" in content
        assert "120.5" in content
        assert "1.25" in content

    def test_multiple_intersections(self, sample_intersection):
        """Should handle multiple intersections."""
        int2 = sample_intersection.model_copy()
        int2.name = "Second St & 2nd Ave"

        scenario = ScenarioResult(
            scenario_type=ScenarioType.EXISTING,
            scenario_name="Existing",
            intersections=[sample_intersection, int2]
        )

        result = generate_narrative(scenario=scenario)

        # Should have intro + 2 intersection sections
        assert len(result.sections) >= 3
