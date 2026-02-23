"""
Report narrative generation service.

Main entry point for generating TIA report narratives.
All generated text uses only provided data - no hallucinations.
"""

import hashlib
import json
from typing import Optional

from .models import (
    LOS,
    IntersectionResult,
    ScenarioResult,
    ScenarioComparison,
    NarrativeSection,
    ReportNarrative,
)
from .narratives import (
    generate_executive_summary,
    generate_intersection_analysis,
    generate_comparison_paragraph,
    generate_compliance_statement,
    generate_single_intersection_narrative,
)


def _compute_data_hash(data: dict) -> str:
    """Compute a hash of the input data for verification."""
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(json_str.encode()).hexdigest()[:12]


def generate_narrative(
    comparison: Optional[ScenarioComparison] = None,
    intersection: Optional[IntersectionResult] = None,
    scenario: Optional[ScenarioResult] = None,
    threshold_los: Optional[LOS] = None,
    threshold_vc: Optional[float] = None,
    jurisdiction: Optional[str] = None,
    include_lane_groups: bool = False,
) -> ReportNarrative:
    """
    Generate complete report narrative.

    Accepts either:
    - A scenario comparison (baseline vs proposed)
    - A single scenario with multiple intersections
    - A single intersection result

    Args:
        comparison: Scenario comparison (baseline vs proposed)
        intersection: Single intersection result
        scenario: Single scenario result
        threshold_los: LOS threshold for compliance (user-provided)
        threshold_vc: V/C threshold for compliance (user-provided)
        jurisdiction: Jurisdiction name (for compliance statement)
        include_lane_groups: Whether to include lane group details

    Returns:
        ReportNarrative with structured sections

    Example:
        >>> from report_generator import generate_narrative, ScenarioComparison
        >>> narrative = generate_narrative(
        ...     comparison=comparison,
        ...     threshold_los=LOS.D,
        ...     jurisdiction="City of Example"
        ... )
        >>> for section in narrative.sections:
        ...     print(f"## {section.title}")
        ...     print(section.content)
    """
    sections: list[NarrativeSection] = []
    generated_from = "Unknown"
    data_hash = None

    if comparison is not None:
        # Full comparison narrative
        generated_from = "ScenarioComparison"
        data_hash = _compute_data_hash(comparison.model_dump())

        # Executive summary
        sections.append(generate_executive_summary(comparison))

        # Per-intersection analysis for baseline
        for int_result in comparison.baseline.intersections:
            sections.append(generate_intersection_analysis(
                int_result,
                comparison.baseline.scenario_name
            ))

        # Per-intersection analysis for proposed
        for int_result in comparison.proposed.intersections:
            sections.append(generate_intersection_analysis(
                int_result,
                comparison.proposed.scenario_name
            ))

        # Comparison paragraphs
        for int_result in comparison.baseline.intersections:
            sections.append(generate_comparison_paragraph(
                comparison,
                int_result.name
            ))

        # Compliance statement
        sections.append(generate_compliance_statement(
            comparison,
            threshold_los=threshold_los,
            threshold_vc=threshold_vc,
            jurisdiction=jurisdiction
        ))

    elif scenario is not None:
        # Single scenario narrative
        generated_from = "ScenarioResult"
        data_hash = _compute_data_hash(scenario.model_dump())

        # Intro section
        intro_content = (
            f"The following analysis presents traffic operations for "
            f"{len(scenario.intersections)} intersection(s) under "
            f"{scenario.scenario_name} conditions"
        )
        if scenario.year:
            intro_content += f" for year {scenario.year}"
        intro_content += "."

        if scenario.description:
            intro_content += f" {scenario.description}"

        sections.append(NarrativeSection(
            section_id="introduction",
            title="Introduction",
            content=intro_content
        ))

        # Per-intersection analysis
        for int_result in scenario.intersections:
            sections.append(generate_single_intersection_narrative(int_result))

    elif intersection is not None:
        # Single intersection narrative
        generated_from = "IntersectionResult"
        data_hash = _compute_data_hash(intersection.model_dump())

        sections.append(generate_single_intersection_narrative(intersection))

        # Lane group details if requested
        if include_lane_groups and intersection.lane_groups:
            lg_parts = []
            for lg in intersection.lane_groups:
                lg_text = (
                    f"The {lg.name} ({lg.movement}) operates at "
                    f"{lg.los.value} with {lg.delay:.1f} seconds of delay "
                    f"and a v/c ratio of {lg.vc_ratio:.2f}."
                )
                if lg.queue_95th:
                    lg_text += f" The 95th percentile queue is {lg.queue_95th:.0f} feet."
                lg_parts.append(lg_text)

            sections.append(NarrativeSection(
                section_id="lane_group_details",
                title="Lane Group Details",
                content=" ".join(lg_parts)
            ))

    else:
        raise ValueError(
            "Must provide either comparison, scenario, or intersection"
        )

    return ReportNarrative(
        sections=sections,
        generated_from=generated_from,
        data_hash=data_hash
    )


def generate_summary_table_caption(
    scenario: ScenarioResult,
    analysis_period: str
) -> str:
    """
    Generate a caption for a summary table.

    Args:
        scenario: Scenario result
        analysis_period: Analysis period description

    Returns:
        Table caption string
    """
    year_text = f" ({scenario.year})" if scenario.year else ""
    return (
        f"Table X: {scenario.scenario_name}{year_text} "
        f"Intersection Level of Service Summary - {analysis_period}"
    )


def generate_queue_table_caption(
    intersection_name: str,
    scenario_name: str
) -> str:
    """
    Generate a caption for a queue table.

    Args:
        intersection_name: Name of the intersection
        scenario_name: Name of the scenario

    Returns:
        Table caption string
    """
    return (
        f"Table X: {intersection_name} Queue Analysis - {scenario_name} Conditions"
    )
