"""
Narrative generation functions.

All narratives are generated from provided data only.
No hallucinated standards, guidelines, or thresholds.
"""

from .models import (
    LOS,
    IntersectionResult,
    ScenarioResult,
    ScenarioComparison,
    NarrativeSection,
)


def _los_descriptor(los: LOS) -> str:
    """Get a factual descriptor for LOS without subjective judgment."""
    descriptors = {
        LOS.A: "LOS A",
        LOS.B: "LOS B",
        LOS.C: "LOS C",
        LOS.D: "LOS D",
        LOS.E: "LOS E",
        LOS.F: "LOS F",
    }
    return descriptors.get(los, str(los))


def _delay_phrase(delay: float) -> str:
    """Format delay for narrative."""
    return f"{delay:.1f} seconds of delay"


def _format_change(baseline: float, proposed: float) -> str:
    """Format the change between two values."""
    diff = proposed - baseline
    if abs(diff) < 0.1:
        return "no significant change"
    elif diff > 0:
        return f"an increase of {diff:.1f} seconds"
    else:
        return f"a decrease of {abs(diff):.1f} seconds"


def _los_changed(baseline: LOS, proposed: LOS) -> str:
    """Describe LOS change factually."""
    if baseline == proposed:
        return f"remained at {baseline.value}"
    else:
        return f"changed from {baseline.value} to {proposed.value}"


# --- Section Generators ---

def generate_executive_summary(
    comparison: ScenarioComparison
) -> NarrativeSection:
    """
    Generate executive summary paragraph.

    Uses only data from the comparison - no external standards.
    """
    baseline = comparison.baseline
    proposed = comparison.proposed

    # Count intersections by LOS in each scenario
    def count_by_los(scenario: ScenarioResult) -> dict:
        counts = {los: 0 for los in LOS}
        for intersection in scenario.intersections:
            counts[intersection.overall_los] += 1
        return counts

    baseline_counts = count_by_los(baseline)
    proposed_counts = count_by_los(proposed)

    # Build summary
    num_intersections = len(baseline.intersections)
    project_desc = ""
    if comparison.project_name:
        project_desc = f"for the {comparison.project_name} "

    trips_desc = ""
    if comparison.project_trips_am and comparison.project_trips_pm:
        trips_desc = (
            f"The project is anticipated to generate {comparison.project_trips_am} "
            f"trips during the AM peak hour and {comparison.project_trips_pm} trips "
            f"during the PM peak hour. "
        )

    # Determine overall findings
    los_e_f_baseline = baseline_counts[LOS.E] + baseline_counts[LOS.F]
    los_e_f_proposed = proposed_counts[LOS.E] + proposed_counts[LOS.F]

    if los_e_f_proposed > los_e_f_baseline:
        impact_stmt = (
            f"The analysis indicates that {los_e_f_proposed - los_e_f_baseline} "
            f"additional intersection(s) would operate at LOS E or F under the "
            f"{proposed.scenario_name} scenario compared to {baseline.scenario_name} conditions."
        )
    elif los_e_f_proposed < los_e_f_baseline:
        impact_stmt = (
            f"The analysis indicates that {los_e_f_baseline - los_e_f_proposed} "
            f"fewer intersection(s) would operate at LOS E or F under the "
            f"{proposed.scenario_name} scenario compared to {baseline.scenario_name} conditions."
        )
    else:
        impact_stmt = (
            f"The analysis indicates that the number of intersections operating at "
            f"LOS E or F would remain unchanged between the {baseline.scenario_name} "
            f"and {proposed.scenario_name} scenarios."
        )

    content = (
        f"A traffic analysis was conducted {project_desc}evaluating "
        f"{num_intersections} intersection(s) under {baseline.scenario_name} "
        f"and {proposed.scenario_name} conditions. {trips_desc}{impact_stmt}"
    )

    return NarrativeSection(
        section_id="executive_summary",
        title="Executive Summary",
        content=content.strip()
    )


def generate_intersection_analysis(
    intersection: IntersectionResult,
    scenario_name: str
) -> NarrativeSection:
    """
    Generate intersection-level analysis paragraph.

    Reports only the provided metrics without interpretation.
    """
    parts = []

    # Opening
    parts.append(
        f"Under {scenario_name} conditions, the {intersection.name} intersection "
        f"({intersection.control_type}) operates at an overall {_los_descriptor(intersection.overall_los)} "
        f"with {_delay_phrase(intersection.overall_delay)} during the {intersection.analysis_period.value} period."
    )

    # Critical v/c if available
    if intersection.overall_vc is not None:
        parts.append(
            f"The critical volume-to-capacity ratio is {intersection.overall_vc:.2f}."
        )

    # Worst approach/movement
    if intersection.worst_approach_name and intersection.worst_approach_los:
        parts.append(
            f"The {intersection.worst_approach_name} approach operates at "
            f"{_los_descriptor(intersection.worst_approach_los)}, "
            f"representing the critical approach."
        )

    if intersection.worst_movement_name and intersection.worst_movement_los:
        parts.append(
            f"The {intersection.worst_movement_name} movement operates at "
            f"{_los_descriptor(intersection.worst_movement_los)}."
        )

    # Cycle length if signalized
    if intersection.cycle_length and intersection.control_type == "Signalized":
        parts.append(
            f"The analysis assumes a {intersection.cycle_length:.0f}-second cycle length."
        )

    # Lane group details if provided
    if intersection.lane_groups:
        los_f_groups = [lg for lg in intersection.lane_groups if lg.los == LOS.F]
        if los_f_groups:
            group_names = ", ".join(lg.name for lg in los_f_groups)
            parts.append(
                f"The following lane group(s) operate at LOS F: {group_names}."
            )

    # Notes
    if intersection.notes:
        parts.append(intersection.notes)

    # Create unique section ID including scenario name
    scenario_slug = scenario_name.lower().replace(' ', '_')
    intersection_slug = intersection.name.lower().replace(' ', '_')

    return NarrativeSection(
        section_id=f"intersection_{intersection_slug}_{scenario_slug}",
        title=f"{intersection.name} Analysis - {scenario_name}",
        content=" ".join(parts)
    )


def generate_comparison_paragraph(
    comparison: ScenarioComparison,
    intersection_name: str
) -> NarrativeSection:
    """
    Generate comparison paragraph between scenarios for an intersection.

    Presents factual comparison without value judgments.
    """
    # Find matching intersections
    baseline_int = next(
        (i for i in comparison.baseline.intersections if i.name == intersection_name),
        None
    )
    proposed_int = next(
        (i for i in comparison.proposed.intersections if i.name == intersection_name),
        None
    )

    if not baseline_int or not proposed_int:
        return NarrativeSection(
            section_id=f"comparison_{intersection_name.lower().replace(' ', '_')}",
            title=f"{intersection_name} Comparison",
            content=f"Comparison data not available for {intersection_name}."
        )

    parts = []

    # LOS comparison
    los_change = _los_changed(baseline_int.overall_los, proposed_int.overall_los)
    parts.append(
        f"At the {intersection_name} intersection, the overall LOS {los_change} "
        f"between the {comparison.baseline.scenario_name} and {comparison.proposed.scenario_name} scenarios."
    )

    # Delay comparison
    delay_change = _format_change(baseline_int.overall_delay, proposed_int.overall_delay)
    parts.append(
        f"The overall intersection delay changed from {baseline_int.overall_delay:.1f} seconds "
        f"to {proposed_int.overall_delay:.1f} seconds, representing {delay_change}."
    )

    # v/c comparison if available
    if baseline_int.overall_vc is not None and proposed_int.overall_vc is not None:
        vc_diff = proposed_int.overall_vc - baseline_int.overall_vc
        if abs(vc_diff) < 0.01:
            parts.append("The critical v/c ratio remained essentially unchanged.")
        else:
            direction = "increased" if vc_diff > 0 else "decreased"
            parts.append(
                f"The critical v/c ratio {direction} from {baseline_int.overall_vc:.2f} "
                f"to {proposed_int.overall_vc:.2f}."
            )

    # Worst movement comparison
    if (baseline_int.worst_movement_name and proposed_int.worst_movement_name and
        baseline_int.worst_movement_name == proposed_int.worst_movement_name):
        if baseline_int.worst_movement_los != proposed_int.worst_movement_los:
            parts.append(
                f"The critical movement ({baseline_int.worst_movement_name}) "
                f"LOS changed from {baseline_int.worst_movement_los.value} "
                f"to {proposed_int.worst_movement_los.value}."
            )

    return NarrativeSection(
        section_id=f"comparison_{intersection_name.lower().replace(' ', '_')}",
        title=f"{intersection_name} Scenario Comparison",
        content=" ".join(parts)
    )


def generate_compliance_statement(
    comparison: ScenarioComparison,
    threshold_los: LOS | None = None,
    threshold_vc: float | None = None,
    jurisdiction: str | None = None
) -> NarrativeSection:
    """
    Generate compliance statement based on provided thresholds.

    IMPORTANT: Only uses thresholds explicitly provided by the user.
    Does NOT assume or hallucinate any standards.
    """
    parts = []

    if not threshold_los and not threshold_vc:
        # No thresholds provided - factual summary only
        parts.append(
            "No specific LOS or v/c thresholds were provided for compliance evaluation. "
            "The results presented above should be compared against applicable local "
            "agency requirements to determine compliance."
        )
    else:
        # Check compliance against provided thresholds
        if jurisdiction:
            parts.append(f"Based on the provided {jurisdiction} thresholds:")
        else:
            parts.append("Based on the provided thresholds:")

        los_order = [LOS.A, LOS.B, LOS.C, LOS.D, LOS.E, LOS.F]

        for intersection in comparison.proposed.intersections:
            compliant = True
            reasons = []

            if threshold_los:
                threshold_idx = los_order.index(threshold_los)
                actual_idx = los_order.index(intersection.overall_los)
                if actual_idx > threshold_idx:
                    compliant = False
                    reasons.append(
                        f"LOS {intersection.overall_los.value} exceeds threshold of LOS {threshold_los.value}"
                    )

            if threshold_vc and intersection.overall_vc:
                if intersection.overall_vc > threshold_vc:
                    compliant = False
                    reasons.append(
                        f"v/c ratio of {intersection.overall_vc:.2f} exceeds threshold of {threshold_vc:.2f}"
                    )

            if compliant:
                parts.append(
                    f"The {intersection.name} intersection meets the specified thresholds."
                )
            else:
                reason_text = "; ".join(reasons)
                parts.append(
                    f"The {intersection.name} intersection does not meet the specified "
                    f"thresholds ({reason_text})."
                )

    return NarrativeSection(
        section_id="compliance_statement",
        title="Compliance Evaluation",
        content=" ".join(parts)
    )


def generate_single_intersection_narrative(
    intersection: IntersectionResult
) -> NarrativeSection:
    """
    Generate narrative for a single intersection without comparison.
    """
    parts = []

    parts.append(
        f"The {intersection.name} intersection was analyzed under "
        f"{intersection.analysis_period.value} conditions."
    )

    parts.append(
        f"The {intersection.control_type.lower()} intersection operates at "
        f"{_los_descriptor(intersection.overall_los)} with {_delay_phrase(intersection.overall_delay)}."
    )

    if intersection.overall_vc is not None:
        parts.append(f"The critical v/c ratio is {intersection.overall_vc:.2f}.")

    if intersection.worst_approach_name:
        parts.append(
            f"The {intersection.worst_approach_name} approach represents the "
            f"critical approach, operating at {_los_descriptor(intersection.worst_approach_los)}."
        )

    # Queue information if available
    queues = [(lg.name, lg.queue_95th) for lg in intersection.lane_groups
              if lg.queue_95th is not None and lg.queue_95th > 0]
    if queues:
        max_queue = max(queues, key=lambda x: x[1])
        parts.append(
            f"The maximum 95th percentile queue of {max_queue[1]:.0f} feet "
            f"occurs at the {max_queue[0]} movement."
        )

    return NarrativeSection(
        section_id=f"analysis_{intersection.name.lower().replace(' ', '_')}",
        title=f"{intersection.name} Analysis Results",
        content=" ".join(parts)
    )
