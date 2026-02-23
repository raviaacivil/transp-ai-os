"""
Suggestion generation for volume corrections.

Generates structured recommendations based on detected anomalies.
"""

from .models import (
    VolumeInput,
    ApproachVolume,
    Anomaly,
    AnomalyType,
    Suggestion,
    SuggestionType,
)


# --- PHF Suggestions ---

def suggest_phf_correction(
    approach: ApproachVolume,
    anomaly: Anomaly,
    area_type: str
) -> Suggestion | None:
    """
    Generate PHF correction suggestion.

    Args:
        approach: Approach data
        anomaly: The PHF anomaly
        area_type: Area type for defaults

    Returns:
        Suggestion for PHF correction, or None
    """
    if anomaly.type not in (
        AnomalyType.PHF_TOO_LOW,
        AnomalyType.PHF_OUT_OF_RANGE,
        AnomalyType.MISSING_DATA
    ):
        return None

    # Determine suggested PHF based on area type
    default_phf = {
        "cbd": 0.92,
        "urban": 0.90,
        "suburban": 0.88,
        "rural": 0.85,
    }.get(area_type, 0.90)

    current = anomaly.current_value or approach.phf

    if current is None:
        # Missing PHF - suggest default
        return Suggestion(
            type=SuggestionType.USE_DEFAULT_VALUE,
            location=approach.name,
            message=f"Use default PHF of {default_phf:.2f} for {area_type} area",
            current_value=None,
            suggested_value=default_phf,
            confidence=0.70,
            rationale=f"No PHF provided; {default_phf:.2f} is typical for {area_type} conditions"
        )

    if current < 0.70:
        # Invalid PHF - suggest minimum
        return Suggestion(
            type=SuggestionType.ADJUST_PHF,
            location=approach.name,
            message=f"Adjust PHF from {current:.2f} to minimum valid value of 0.70",
            current_value=current,
            suggested_value=0.70,
            confidence=0.90,
            rationale="PHF below 0.70 is physically impossible"
        )

    if current < 0.85 and area_type in ("urban", "cbd"):
        # Low PHF - suggest typical
        return Suggestion(
            type=SuggestionType.ADJUST_PHF,
            location=approach.name,
            message=f"Consider adjusting PHF from {current:.2f} to {default_phf:.2f}",
            current_value=current,
            suggested_value=default_phf,
            confidence=0.65,
            rationale=f"PHF of {current:.2f} is unusual for {area_type} areas; "
                      f"verify peak 15-min count or use typical value"
        )

    return None


def suggest_missing_phf(
    approach: ApproachVolume,
    area_type: str
) -> Suggestion | None:
    """
    Suggest PHF when not provided.

    Args:
        approach: Approach data
        area_type: Area type

    Returns:
        Suggestion for default PHF
    """
    if approach.phf is not None:
        return None

    # Can we calculate from volumes?
    if (approach.peak_hour_volume is not None and
        approach.peak_15_min_volume is not None and
        approach.peak_15_min_volume > 0):

        calculated_phf = approach.peak_hour_volume / (4 * approach.peak_15_min_volume)
        calculated_phf = min(1.0, max(0.70, calculated_phf))  # Clamp

        return Suggestion(
            type=SuggestionType.ADJUST_PHF,
            location=approach.name,
            message=f"Calculate PHF as {calculated_phf:.2f} from peak volumes",
            current_value=None,
            suggested_value=round(calculated_phf, 2),
            confidence=0.90,
            rationale="PHF calculated from provided peak hour and 15-minute volumes"
        )

    # Use default
    default_phf = {
        "cbd": 0.92,
        "urban": 0.90,
        "suburban": 0.88,
        "rural": 0.85,
    }.get(area_type, 0.90)

    return Suggestion(
        type=SuggestionType.USE_DEFAULT_VALUE,
        location=approach.name,
        message=f"Use default PHF of {default_phf:.2f}",
        current_value=None,
        suggested_value=default_phf,
        confidence=0.70,
        rationale=f"No PHF or peak volumes provided; using typical value for {area_type}"
    )


# --- Heavy Vehicle Suggestions ---

def suggest_heavy_vehicle_adjustment(
    approach: ApproachVolume,
    anomaly: Anomaly,
    area_type: str
) -> Suggestion | None:
    """
    Suggest heavy vehicle percentage adjustment.

    Args:
        approach: Approach data
        anomaly: The HV anomaly
        area_type: Area type

    Returns:
        Suggestion for HV adjustment
    """
    if anomaly.type != AnomalyType.HIGH_HEAVY_VEHICLE_PCT:
        return None

    current = anomaly.current_value or approach.heavy_vehicle_pct
    if current is None:
        return None

    # Suggest typical values
    typical_hv = {
        "cbd": 3.0,
        "urban": 5.0,
        "suburban": 7.0,
        "rural": 12.0,
    }.get(area_type, 5.0)

    return Suggestion(
        type=SuggestionType.VERIFY_COUNT,
        location=approach.name,
        message=f"Verify heavy vehicle count ({current:.1f}%); typical is {typical_hv:.1f}%",
        current_value=current,
        suggested_value=typical_hv,
        confidence=0.50,
        rationale=f"Heavy vehicle percentage of {current:.1f}% is above typical; "
                  f"verify classification counts or check for nearby truck generators"
    )


# --- Growth Factor Suggestions ---

def suggest_growth_adjustment(inputs: VolumeInput) -> list[Suggestion]:
    """
    Suggest growth factor application if needed.

    Args:
        inputs: Volume input with year information

    Returns:
        List of growth-related suggestions
    """
    suggestions = []

    if inputs.base_year and inputs.analysis_year:
        years_diff = inputs.analysis_year - inputs.base_year

        if years_diff > 0:
            # Use provided growth rate or suggest typical
            if inputs.annual_growth_rate is not None:
                growth_rate = inputs.annual_growth_rate
                confidence = 0.85
                rationale = f"Using provided annual growth rate of {growth_rate:.1f}%"
            else:
                # Suggest typical growth by area
                growth_rate = {
                    "cbd": 0.5,
                    "urban": 1.0,
                    "suburban": 2.0,
                    "rural": 1.5,
                }.get(inputs.area_type, 1.0)
                confidence = 0.60
                rationale = f"Using typical growth rate for {inputs.area_type} areas"

            # Calculate compound growth factor
            growth_factor = (1 + growth_rate / 100) ** years_diff

            suggestions.append(Suggestion(
                type=SuggestionType.APPLY_GROWTH_FACTOR,
                location="All approaches",
                message=f"Apply growth factor of {growth_factor:.3f} "
                        f"({years_diff} years at {growth_rate:.1f}%/year)",
                current_value=1.0,
                suggested_value=round(growth_factor, 3),
                confidence=confidence,
                rationale=rationale
            ))

    return suggestions


# --- Volume Verification Suggestions ---

def suggest_volume_verification(
    approach: ApproachVolume,
    anomaly: Anomaly
) -> Suggestion | None:
    """
    Suggest volume verification for suspicious values.

    Args:
        approach: Approach data
        anomaly: Volume anomaly

    Returns:
        Verification suggestion
    """
    if anomaly.type == AnomalyType.ZERO_VOLUME:
        return Suggestion(
            type=SuggestionType.VERIFY_COUNT,
            location=approach.name,
            message="Verify if approach is closed or count is missing",
            current_value=0,
            suggested_value=None,
            confidence=0.50,
            rationale="Zero volume may indicate closed approach, missing data, or count error"
        )

    if anomaly.type == AnomalyType.SUSPICIOUS_ROUND_NUMBER:
        return Suggestion(
            type=SuggestionType.VERIFY_COUNT,
            location=anomaly.location,
            message=f"Verify count of {anomaly.current_value:.0f} - may be estimated",
            current_value=anomaly.current_value,
            suggested_value=None,
            confidence=0.40,
            rationale="Round numbers often indicate estimates rather than actual counts"
        )

    if anomaly.type == AnomalyType.UNREALISTIC_HIGH_VOLUME:
        return Suggestion(
            type=SuggestionType.VERIFY_COUNT,
            location=approach.name,
            message=f"Verify high volume of {anomaly.current_value:.0f} vph",
            current_value=anomaly.current_value,
            suggested_value=None,
            confidence=0.60,
            rationale="Volume exceeds typical capacity; verify lane count and count accuracy"
        )

    return None


# --- Main Suggestion Function ---

def generate_suggestions(
    inputs: VolumeInput,
    anomalies: list[Anomaly]
) -> list[Suggestion]:
    """
    Generate all suggestions based on inputs and detected anomalies.

    Args:
        inputs: Volume input data
        anomalies: List of detected anomalies

    Returns:
        Complete list of suggestions
    """
    suggestions: list[Suggestion] = []

    # Group anomalies by approach
    approach_anomalies: dict[str, list[Anomaly]] = {}
    for anomaly in anomalies:
        loc = anomaly.location.split("/")[0]  # Get base approach name
        if loc not in approach_anomalies:
            approach_anomalies[loc] = []
        approach_anomalies[loc].append(anomaly)

    # Generate suggestions for each approach
    for approach in inputs.approaches:
        # Check for missing PHF
        phf_suggestion = suggest_missing_phf(approach, inputs.area_type)
        if phf_suggestion:
            suggestions.append(phf_suggestion)

        # Process anomalies for this approach
        for anomaly in approach_anomalies.get(approach.name, []):
            # PHF corrections
            s = suggest_phf_correction(approach, anomaly, inputs.area_type)
            if s:
                suggestions.append(s)

            # HV adjustments
            s = suggest_heavy_vehicle_adjustment(approach, anomaly, inputs.area_type)
            if s:
                suggestions.append(s)

            # Volume verification
            s = suggest_volume_verification(approach, anomaly)
            if s:
                suggestions.append(s)

    # Growth factor suggestions
    suggestions.extend(suggest_growth_adjustment(inputs))

    # Remove duplicates (same type + location)
    seen = set()
    unique_suggestions = []
    for s in suggestions:
        key = (s.type, s.location)
        if key not in seen:
            seen.add(key)
            unique_suggestions.append(s)

    return unique_suggestions
