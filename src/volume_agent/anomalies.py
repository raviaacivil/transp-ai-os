"""
Anomaly detection rules for volume data.

Each detector is a pure function that returns a list of anomalies.
"""

from .models import (
    VolumeInput,
    ApproachVolume,
    Anomaly,
    AnomalyType,
    AnomalySeverity,
)


# --- PHF Anomaly Detection ---

def detect_phf_anomalies(
    approach: ApproachVolume,
    area_type: str
) -> list[Anomaly]:
    """
    Detect PHF-related anomalies.

    PHF thresholds by area type:
        - Urban/CBD: 0.85-0.98 typical
        - Suburban: 0.80-0.95 typical
        - Rural: 0.70-0.90 typical

    Args:
        approach: Approach volume data
        area_type: Area type for context

    Returns:
        List of PHF anomalies
    """
    anomalies = []

    if approach.phf is None:
        anomalies.append(Anomaly(
            type=AnomalyType.MISSING_DATA,
            severity=AnomalySeverity.INFO,
            location=approach.name,
            message=f"PHF not provided for {approach.name}",
            expected_range="0.85-0.95 typical"
        ))
        return anomalies

    phf = approach.phf

    # Absolute bounds
    if phf < 0.70:
        anomalies.append(Anomaly(
            type=AnomalyType.PHF_OUT_OF_RANGE,
            severity=AnomalySeverity.ERROR,
            location=approach.name,
            message=f"PHF of {phf:.2f} is below minimum valid value of 0.70",
            current_value=phf,
            expected_range="0.70-1.00"
        ))
    elif phf > 1.0:
        anomalies.append(Anomaly(
            type=AnomalyType.PHF_OUT_OF_RANGE,
            severity=AnomalySeverity.ERROR,
            location=approach.name,
            message=f"PHF of {phf:.2f} exceeds maximum of 1.00",
            current_value=phf,
            expected_range="0.70-1.00"
        ))

    # Context-specific thresholds
    if area_type in ("urban", "cbd"):
        if 0.70 <= phf < 0.85:
            anomalies.append(Anomaly(
                type=AnomalyType.PHF_TOO_LOW,
                severity=AnomalySeverity.WARNING,
                location=approach.name,
                message=f"PHF of {phf:.2f} is below typical minimum of 0.85 for {area_type} areas",
                current_value=phf,
                expected_range="0.85-0.95"
            ))
        elif phf > 0.98:
            anomalies.append(Anomaly(
                type=AnomalyType.PHF_TOO_HIGH,
                severity=AnomalySeverity.INFO,
                location=approach.name,
                message=f"PHF of {phf:.2f} is unusually high - verify peak 15-min count",
                current_value=phf,
                expected_range="0.85-0.95"
            ))
    elif area_type == "suburban":
        if 0.70 <= phf < 0.80:
            anomalies.append(Anomaly(
                type=AnomalyType.PHF_TOO_LOW,
                severity=AnomalySeverity.WARNING,
                location=approach.name,
                message=f"PHF of {phf:.2f} is below typical minimum of 0.80 for suburban areas",
                current_value=phf,
                expected_range="0.80-0.95"
            ))

    return anomalies


# --- Heavy Vehicle Anomaly Detection ---

def detect_heavy_vehicle_anomalies(
    approach: ApproachVolume,
    area_type: str,
    facility_type: str
) -> list[Anomaly]:
    """
    Detect heavy vehicle percentage anomalies.

    Typical HV% by context:
        - Urban arterial: 2-5%
        - Suburban arterial: 3-8%
        - Rural arterial: 5-15%
        - Near industrial: 10-25%

    Args:
        approach: Approach volume data
        area_type: Area type
        facility_type: Facility type

    Returns:
        List of heavy vehicle anomalies
    """
    anomalies = []

    if approach.heavy_vehicle_pct is None:
        return anomalies

    hv_pct = approach.heavy_vehicle_pct

    # Set thresholds by context
    if area_type == "cbd":
        high_threshold = 5.0
        very_high_threshold = 10.0
        expected = "2-5%"
    elif area_type == "urban":
        high_threshold = 8.0
        very_high_threshold = 15.0
        expected = "2-8%"
    elif area_type == "suburban":
        high_threshold = 12.0
        very_high_threshold = 20.0
        expected = "3-12%"
    else:  # rural
        high_threshold = 20.0
        very_high_threshold = 30.0
        expected = "5-20%"

    if hv_pct > very_high_threshold:
        anomalies.append(Anomaly(
            type=AnomalyType.HIGH_HEAVY_VEHICLE_PCT,
            severity=AnomalySeverity.WARNING,
            location=approach.name,
            message=f"Heavy vehicle percentage of {hv_pct:.1f}% is very high for {area_type} {facility_type}",
            current_value=hv_pct,
            expected_range=expected
        ))
    elif hv_pct > high_threshold:
        anomalies.append(Anomaly(
            type=AnomalyType.HIGH_HEAVY_VEHICLE_PCT,
            severity=AnomalySeverity.INFO,
            location=approach.name,
            message=f"Heavy vehicle percentage of {hv_pct:.1f}% is above typical for {area_type} {facility_type}",
            current_value=hv_pct,
            expected_range=expected
        ))

    return anomalies


# --- Volume Anomaly Detection ---

def detect_volume_anomalies(
    approach: ApproachVolume,
    area_type: str,
    facility_type: str
) -> list[Anomaly]:
    """
    Detect volume-related anomalies.

    Checks for:
        - Zero volumes
        - Very low volumes
        - Unrealistically high volumes
        - Suspicious round numbers

    Args:
        approach: Approach volume data
        area_type: Area type
        facility_type: Facility type

    Returns:
        List of volume anomalies
    """
    anomalies = []
    total = approach.movements.total

    # Zero volume check
    if total == 0:
        anomalies.append(Anomaly(
            type=AnomalyType.ZERO_VOLUME,
            severity=AnomalySeverity.WARNING,
            location=approach.name,
            message=f"Zero total volume for {approach.name} - verify if approach is closed",
            current_value=0
        ))
        return anomalies

    # Very low volume check
    low_threshold = 50 if area_type in ("urban", "cbd") else 20
    if total < low_threshold:
        anomalies.append(Anomaly(
            type=AnomalyType.VERY_LOW_VOLUME,
            severity=AnomalySeverity.INFO,
            location=approach.name,
            message=f"Very low volume ({total:.0f} vph) for {approach.name}",
            current_value=total,
            expected_range=f">{low_threshold} vph typical"
        ))

    # High volume check (per lane equivalent)
    # Assume 2 lanes if not specified, ~900 vph/lane is high
    high_per_lane = 900
    assumed_lanes = 2
    high_threshold = high_per_lane * assumed_lanes * 1.5

    if total > high_threshold:
        anomalies.append(Anomaly(
            type=AnomalyType.UNREALISTIC_HIGH_VOLUME,
            severity=AnomalySeverity.WARNING,
            location=approach.name,
            message=f"Volume of {total:.0f} vph may be unrealistically high - verify count",
            current_value=total,
            expected_range=f"<{high_threshold:.0f} vph typical"
        ))

    # Suspicious round numbers
    for movement_name, value in [
        ("left", approach.movements.left),
        ("through", approach.movements.through),
        ("right", approach.movements.right)
    ]:
        if value > 0 and value % 100 == 0 and value >= 200:
            anomalies.append(Anomaly(
                type=AnomalyType.SUSPICIOUS_ROUND_NUMBER,
                severity=AnomalySeverity.INFO,
                location=f"{approach.name}/{movement_name}",
                message=f"Volume of {value:.0f} is a round number - may be estimated",
                current_value=value
            ))

    return anomalies


# --- Volume Balance Check ---

def detect_volume_imbalance(inputs: VolumeInput) -> list[Anomaly]:
    """
    Detect volume imbalances between approaches.

    For a typical 4-way intersection:
        - Opposing approaches should be within ~30% of each other
        - Total entering should roughly equal total exiting

    Args:
        inputs: Complete volume input

    Returns:
        List of imbalance anomalies
    """
    anomalies = []

    # Check if we have opposing approaches (simple heuristic)
    approach_map = {a.name.lower(): a for a in inputs.approaches}

    opposing_pairs = [
        ("northbound", "southbound"),
        ("nb", "sb"),
        ("eastbound", "westbound"),
        ("eb", "wb"),
    ]

    for dir1, dir2 in opposing_pairs:
        a1 = approach_map.get(dir1)
        a2 = approach_map.get(dir2)

        if a1 and a2:
            total1 = a1.movements.total
            total2 = a2.movements.total

            if total1 > 0 and total2 > 0:
                ratio = max(total1, total2) / min(total1, total2)
                if ratio > 2.0:
                    anomalies.append(Anomaly(
                        type=AnomalyType.VOLUME_IMBALANCE,
                        severity=AnomalySeverity.INFO,
                        location=f"{a1.name} vs {a2.name}",
                        message=f"Significant imbalance between opposing approaches ({total1:.0f} vs {total2:.0f} vph)",
                        current_value=ratio,
                        expected_range="Ratio < 2.0"
                    ))

    return anomalies


# --- PHF Consistency Check ---

def detect_phf_volume_mismatch(approach: ApproachVolume) -> list[Anomaly]:
    """
    Check if PHF is consistent with peak hour and peak 15-min volumes.

    PHF = Peak Hour Volume / (4 × Peak 15-min Volume)

    Args:
        approach: Approach volume data

    Returns:
        List of mismatch anomalies
    """
    anomalies = []

    if (approach.phf is not None and
        approach.peak_hour_volume is not None and
        approach.peak_15_min_volume is not None and
        approach.peak_15_min_volume > 0):

        calculated_phf = approach.peak_hour_volume / (4 * approach.peak_15_min_volume)
        diff = abs(calculated_phf - approach.phf)

        if diff > 0.05:
            anomalies.append(Anomaly(
                type=AnomalyType.PEAK_HOUR_MISMATCH,
                severity=AnomalySeverity.WARNING,
                location=approach.name,
                message=f"Provided PHF ({approach.phf:.2f}) doesn't match calculated PHF ({calculated_phf:.2f})",
                current_value=approach.phf,
                expected_range=f"{calculated_phf:.2f}"
            ))

    return anomalies


# --- Main Detection Function ---

def detect_all_anomalies(inputs: VolumeInput) -> list[Anomaly]:
    """
    Run all anomaly detection checks.

    Args:
        inputs: Volume input data

    Returns:
        Complete list of detected anomalies
    """
    all_anomalies: list[Anomaly] = []

    for approach in inputs.approaches:
        # PHF checks
        all_anomalies.extend(
            detect_phf_anomalies(approach, inputs.area_type)
        )

        # Heavy vehicle checks
        all_anomalies.extend(
            detect_heavy_vehicle_anomalies(
                approach, inputs.area_type, inputs.facility_type
            )
        )

        # Volume checks
        all_anomalies.extend(
            detect_volume_anomalies(
                approach, inputs.area_type, inputs.facility_type
            )
        )

        # PHF consistency
        all_anomalies.extend(
            detect_phf_volume_mismatch(approach)
        )

    # Cross-approach checks
    all_anomalies.extend(detect_volume_imbalance(inputs))

    return all_anomalies
