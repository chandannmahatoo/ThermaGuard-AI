"""One deterministic event, feature, baseline and decision-support pipeline."""

import hashlib
import math
import statistics
from datetime import datetime, timezone, timedelta

from pyproj import Geod

from .config import settings


GEOD = Geod(ellps="WGS84")

FEATURE_VERSION = "2"

# Historical baseline policy
MIN_BASELINE_EVENTS = 5
HISTORICAL_RADIUS_KM = 5.0
HISTORICAL_WINDOW_DAYS = 365


FEATURES = [
    "mean_frp",
    "max_frp",
    "mean_brightness",
    "max_brightness",
    "quality_mean",
    "duration_hours",
    "detection_count",
    "night_fraction",
    "spatial_spread_km",
    "persistence_days",
    "detection_frequency",
    "recurrence_count",
    "historical_mean_frp",
    "historical_max_frp",
    "historical_std_frp",
    "historical_baseline_available",
    "distance_to_industrial_m",
    "distance_to_refinery_m",
    "distance_to_powerplant_m",
    "distance_to_factory_m",
    "distance_to_forest_m",
    "distance_to_farmland_m",
    "distance_to_residential_m",
    "nearby_industrial_count",
    "nearby_facility_count",
    "ndvi",
    "vegetation_fraction",
    "built_up_fraction",
    "landuse_industrial",
    "landuse_forest",
    "landuse_farmland",
]


CLASSES = [
    "industrial_fire",
    "persistent_industrial_thermal_source",
    "agricultural_vegetation_fire",
    "natural_thermal_event",
    "possible_false_positive",
]


# ============================================================
# GEOSPATIAL DISTANCE
# ============================================================

def distance(a, b):
    """
    Geodesic distance between two dictionaries containing
    latitude and longitude.

    Returns distance in kilometres.
    """

    return (
        GEOD.inv(
            a["longitude"],
            a["latitude"],
            b["longitude"],
            b["latitude"],
        )[2]
        / 1000
    )


# ============================================================
# FIRMS OBSERVATION VALIDATION
# ============================================================

def validate(row, is_demo=False):
    """
    Validate and normalize one NASA FIRMS observation.
    """

    lat = float(row["latitude"])
    lon = float(row["longitude"])

    if (
        not math.isfinite(lat)
        or not math.isfinite(lon)
        or not (-90 <= lat <= 90)
        or not (-180 <= lon <= 180)
    ):
        raise ValueError("Invalid coordinates")

    observed = datetime.strptime(
        f"{row['acq_date']} {str(row['acq_time']).zfill(4)}",
        "%Y-%m-%d %H%M",
    ).replace(tzinfo=timezone.utc)

    frp = float(row["frp"])

    brightness = float(
        row.get("bright_ti4")
        or row.get("brightness")
    )

    if not all(
        math.isfinite(value) and value >= 0
        for value in (frp, brightness)
    ):
        raise ValueError("Invalid thermal value")

    identity = "|".join(
        str(row.get(key, ""))
        for key in [
            "latitude",
            "longitude",
            "acq_date",
            "acq_time",
            "satellite",
            "instrument",
        ]
    )

    source_id = hashlib.sha256(
        identity.encode()
    ).hexdigest()[:20]

    return {
        "id":
            ("demo-" if is_demo else "firms-")
            + source_id,

        "source":
            "deterministic_fixture"
            if is_demo
            else "NASA FIRMS",

        "source_id":
            source_id,

        "provider":
            "demo"
            if is_demo
            else "NASA",

        "processing_version":
            "1",

        "retrieved_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "observed_at":
            observed.isoformat(),

        "latitude":
            lat,

        "longitude":
            lon,

        "frp":
            frp,

        "brightness":
            brightness,

        "confidence":
            row.get("confidence"),

        "satellite":
            row.get("satellite"),

        "instrument":
            row.get("instrument"),

        "day_night":
            row.get("daynight", "U"),

        "is_demo":
            is_demo,

        "raw":
            row,
    }


# ============================================================
# FIRMS QUALITY
# ============================================================

def quality(row):
    """
    Convert FIRMS confidence representation into 0..1 quality.
    """

    value = str(
        row.get("confidence") or ""
    ).lower()

    if value in {"l", "n", "h"}:
        return {
            "l": 0.0,
            "n": 0.5,
            "h": 1.0,
        }[value]

    try:
        number = float(value)

        if (
            math.isfinite(number)
            and 0 <= number <= 100
        ):
            return number / 100

        return None

    except ValueError:
        return None


# ============================================================
# SPATIOTEMPORAL EVENT CLUSTERING
# ============================================================

def cluster(rows):
    """
    Group nearby FIRMS observations into thermal events.

    Uses configured spatial and temporal clustering thresholds.
    """

    rows = sorted(
        {
            row["id"]: row
            for row in rows
        }.values(),
        key=lambda row: (
            row["observed_at"],
            row["id"],
        ),
    )

    parents = list(
        range(len(rows))
    )

    def root(index):
        while parents[index] != index:
            parents[index] = parents[
                parents[index]
            ]

            index = parents[index]

        return index

    for i, observation_a in enumerate(rows):

        for j in range(i):

            observation_b = rows[j]

            time_difference = abs(
                (
                    datetime.fromisoformat(
                        observation_a["observed_at"]
                    )
                    - datetime.fromisoformat(
                        observation_b["observed_at"]
                    )
                ).total_seconds()
            )

            same_data_type = (
                observation_a["is_demo"]
                == observation_b["is_demo"]
            )

            close_in_time = (
                time_difference
                <= settings.event_cluster_time_hours
                * 3600
            )

            close_in_space = (
                distance(
                    observation_a,
                    observation_b,
                )
                <= settings.event_cluster_radius_km
            )

            if (
                same_data_type
                and close_in_time
                and close_in_space
            ):
                parents[root(i)] = root(j)

    groups = {}

    for i, row in enumerate(rows):
        groups.setdefault(
            root(i),
            [],
        ).append(row)

    events = []

    for group in groups.values():

        first = group[0]
        last = group[-1]

        center = {
            "latitude":
                sum(
                    row["latitude"]
                    for row in group
                )
                / len(group),

            "longitude":
                sum(
                    row["longitude"]
                    for row in group
                )
                / len(group),
        }

        qualities = [
            quality(row)
            for row in group
            if quality(row) is not None
        ]

        start_time = datetime.fromisoformat(
            first["observed_at"]
        )

        last_time = datetime.fromisoformat(
            last["observed_at"]
        )

        duration_hours = (
            last_time - start_time
        ).total_seconds() / 3600

        event = {
            "quality_mean":
                (
                    sum(qualities)
                    / len(qualities)
                    if qualities
                    else None
                ),

            "id":
                "TG-" + first["id"],

            **center,

            "is_demo":
                first["is_demo"],

            "start_time":
                first["observed_at"],

            "last_seen_time":
                last["observed_at"],

            "duration_hours":
                duration_hours,

            "detection_count":
                len(group),

            "mean_frp":
                sum(
                    row["frp"]
                    for row in group
                )
                / len(group),

            "max_frp":
                max(
                    row["frp"]
                    for row in group
                ),

            "mean_brightness":
                sum(
                    row["brightness"]
                    for row in group
                )
                / len(group),

            "max_brightness":
                max(
                    row["brightness"]
                    for row in group
                ),

            "spatial_spread_km":
                max(
                    distance(
                        center,
                        row,
                    )
                    for row in group
                ),

            "night_fraction":
                sum(
                    row["day_night"] == "N"
                    for row in group
                )
                / len(group),

            "day_detection_count":
                sum(
                    row["day_night"] == "D"
                    for row in group
                ),

            "night_detection_count":
                sum(
                    row["day_night"] == "N"
                    for row in group
                ),

            "persistence_days":
                len(
                    {
                        row["observed_at"][:10]
                        for row in group
                    }
                ),

            "detection_ids":
                [
                    row["id"]
                    for row in group
                ],

            "status":
                "monitoring",
        }

        events.append(event)

    return events


# ============================================================
# ML FEATURE VECTOR
# ============================================================

def features(event):
    """
    Convert one event into the deterministic ML feature vector.
    """

    merged = {
        **event,
        **event.get(
            "context",
            {},
        ),
        **event.get(
            "history",
            {},
        ),
    }

    if "context" in event:

        landuse = event[
            "context"
        ].get(
            "landuse_class"
        )

        merged.update(
            {
                f"landuse_{kind}":
                    (
                        float(
                            landuse == kind
                        )
                        if landuse
                        else None
                    )

                for kind in [
                    "industrial",
                    "forest",
                    "farmland",
                ]
            }
        )

    return [
        (
            float(merged[key])
            if merged.get(key) is not None
            else float("nan")
        )
        for key in FEATURES
    ]


# ============================================================
# HISTORICAL BASELINE
# ============================================================

def historical_context(event, historical):
    """
    Calculate historical context for one current thermal event.

    A baseline is considered statistically usable only when at
    least MIN_BASELINE_EVENTS legitimate previous events exist
    within HISTORICAL_RADIUS_KM and HISTORICAL_WINDOW_DAYS.

    Demo data is never mixed with real data.
    """

    try:
        current_start = datetime.fromisoformat(
            event["start_time"]
        )

        if current_start.tzinfo is None:
            current_start = current_start.replace(
                tzinfo=timezone.utc
            )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        raise ValueError(
            "Event has invalid start_time"
        )

    history_start = (
        current_start
        - timedelta(
            days=HISTORICAL_WINDOW_DAYS
        )
    )

    earlier = []

    for previous in historical:

        try:
            if (
                previous.get("is_demo")
                != event.get("is_demo")
            ):
                continue

            previous_time = datetime.fromisoformat(
                previous["last_seen_time"]
            )

            if previous_time.tzinfo is None:
                previous_time = (
                    previous_time.replace(
                        tzinfo=timezone.utc
                    )
                )

            # Must genuinely precede current event
            if previous_time >= current_start:
                continue

            # Only use the configured history window
            if previous_time < history_start:
                continue

            # Nearby historical event only
            if (
                distance(
                    previous,
                    event,
                )
                > HISTORICAL_RADIUS_KM
            ):
                continue

            earlier.append(previous)

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

    recurrence_count = len(
        earlier
    )

    baseline_available = (
        recurrence_count
        >= MIN_BASELINE_EVENTS
    )

    # --------------------------------------------------------
    # Current event frequency
    # --------------------------------------------------------

    detection_frequency = (
        event["detection_count"]
        / max(
            event["duration_hours"],
            1,
        )
    )

    # --------------------------------------------------------
    # Time-of-day pattern
    # --------------------------------------------------------

    if event["night_fraction"] > 0.5:
        time_of_day_pattern = (
            "night_dominant"
        )

    elif event["night_fraction"] < 0.5:
        time_of_day_pattern = (
            "day_dominant"
        )

    else:
        time_of_day_pattern = (
            "mixed"
        )

    # --------------------------------------------------------
    # Not enough genuine history
    # --------------------------------------------------------

    if not baseline_available:

        return {
            "historical_baseline_available":
                False,

            "historical_event_count":
                recurrence_count,

            "recurrence_count":
                recurrence_count,

            "historical_mean_frp":
                None,

            "historical_max_frp":
                None,

            "historical_std_frp":
                None,

            "historical_mean_brightness":
                None,

            "historical_mean_spread_km":
                None,

            "historical_mean_duration_hours":
                None,

            "historical_mean_frequency":
                None,

            "detection_frequency":
                detection_frequency,

            "time_of_day_pattern":
                time_of_day_pattern,

            "history_window_days":
                HISTORICAL_WINDOW_DAYS,

            "history_radius_km":
                HISTORICAL_RADIUS_KM,

            "minimum_baseline_events":
                MIN_BASELINE_EVENTS,

            "reason":
                "insufficient_history",
        }

    # --------------------------------------------------------
    # Helper for legitimate numerical values
    # --------------------------------------------------------

    def values(key):
        result = []

        for previous in earlier:

            value = previous.get(key)

            if value is None:
                continue

            try:
                numeric = float(value)

                if math.isfinite(numeric):
                    result.append(
                        numeric
                    )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return result

    frp_values = values(
        "mean_frp"
    )

    max_frp_values = values(
        "max_frp"
    )

    brightness_values = values(
        "mean_brightness"
    )

    spread_values = values(
        "spatial_spread_km"
    )

    duration_values = values(
        "duration_hours"
    )

    frequency_values = []

    for previous in earlier:

        try:
            frequency = (
                float(
                    previous[
                        "detection_count"
                    ]
                )
                / max(
                    float(
                        previous[
                            "duration_hours"
                        ]
                    ),
                    1,
                )
            )

            if math.isfinite(
                frequency
            ):
                frequency_values.append(
                    frequency
                )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

    # --------------------------------------------------------
    # Real historical baseline
    # --------------------------------------------------------

    return {
        "historical_baseline_available":
            True,

        "historical_event_count":
            recurrence_count,

        "recurrence_count":
            recurrence_count,

        "historical_mean_frp":
            (
                statistics.mean(
                    frp_values
                )
                if frp_values
                else None
            ),

        "historical_max_frp":
            (
                max(
                    max_frp_values
                )
                if max_frp_values
                else None
            ),

        "historical_std_frp":
            (
                statistics.pstdev(
                    frp_values
                )
                if len(
                    frp_values
                ) >= 2
                else 0.0
            ),

        "historical_mean_brightness":
            (
                statistics.mean(
                    brightness_values
                )
                if brightness_values
                else None
            ),

        "historical_mean_spread_km":
            (
                statistics.mean(
                    spread_values
                )
                if spread_values
                else None
            ),

        "historical_mean_duration_hours":
            (
                statistics.mean(
                    duration_values
                )
                if duration_values
                else None
            ),

        "historical_mean_frequency":
            (
                statistics.mean(
                    frequency_values
                )
                if frequency_values
                else None
            ),

        "detection_frequency":
            detection_frequency,

        "time_of_day_pattern":
            time_of_day_pattern,

        "history_window_days":
            HISTORICAL_WINDOW_DAYS,

        "history_radius_km":
            HISTORICAL_RADIUS_KM,

        "minimum_baseline_events":
            MIN_BASELINE_EVENTS,

        "reason":
            None,
    }


# ============================================================
# RISK + ABNORMALITY ASSESSMENT
# ============================================================

def assess(event, historical):
    """
    Calculate historical abnormality and decision-support risk.

    Classification confidence and risk score remain separate.
    """

    history = (
        event.get("history")
        or historical_context(
            event,
            historical,
        )
    )

    comparisons = {
        "frp": (
            "mean_frp",
            "historical_mean_frp",
        ),

        "brightness": (
            "mean_brightness",
            "historical_mean_brightness",
        ),

        "spatial_spread": (
            "spatial_spread_km",
            "historical_mean_spread_km",
        ),

        "persistence": (
            "duration_hours",
            "historical_mean_duration_hours",
        ),
    }

    ratios = {}

    # --------------------------------------------------------
    # Only calculate abnormality when baseline is valid
    # --------------------------------------------------------

    if history.get(
        "historical_baseline_available"
    ):

        for (
            name,
            (
                current_key,
                baseline_key,
            ),
        ) in comparisons.items():

            baseline_value = history.get(
                baseline_key
            )

            current_value = event.get(
                current_key
            )

            if (
                baseline_value is not None
                and baseline_value > 0
                and current_value is not None
            ):
                ratios[
                    f"{name}_ratio"
                ] = (
                    current_value
                    / baseline_value
                )

            else:
                ratios[
                    f"{name}_ratio"
                ] = None

        historical_frequency = history.get(
            "historical_mean_frequency"
        )

        if (
            historical_frequency is not None
            and historical_frequency > 0
        ):
            ratios[
                "frequency_ratio"
            ] = (
                history[
                    "detection_frequency"
                ]
                / historical_frequency
            )

        else:
            ratios[
                "frequency_ratio"
            ] = None

    else:
        ratios = {
            "frp_ratio":
                None,

            "brightness_ratio":
                None,

            "spatial_spread_ratio":
                None,

            "persistence_ratio":
                None,

            "frequency_ratio":
                None,
        }

    known = [
        value
        for value in ratios.values()
        if value is not None
        and math.isfinite(value)
    ]

    # --------------------------------------------------------
    # Abnormality score
    # --------------------------------------------------------

    if (
        history.get(
            "historical_baseline_available"
        )
        and known
    ):

        maximum_ratio = max(
            known
        )

        deviation = min(
            100,
            max(
                0,
                (
                    maximum_ratio
                    - 1
                )
                * 50,
            ),
        )

        abnormality_status = (
            "above_baseline"
            if maximum_ratio > 1.5
            else "within_baseline"
        )

    else:
        deviation = None
        abnormality_status = (
            "unavailable"
        )

    abnormality = {
        "baseline_available":
            history.get(
                "historical_baseline_available",
                False,
            ),

        "abnormality_score":
            deviation,

        "abnormality_status":
            abnormality_status,

        "reason":
            history.get(
                "reason"
            ),

        "explanation_features": {
            **ratios,

            "historical_event_count":
                history.get(
                    "historical_event_count",
                    history.get(
                        "recurrence_count",
                        0,
                    ),
                ),
        },

        "historical_mean_frp":
            history.get(
                "historical_mean_frp"
            ),
    }

    # --------------------------------------------------------
    # Context-based risk components
    # --------------------------------------------------------

    context = event.get(
        "context",
        {},
    )

    def nearby(key):
        value = context.get(
            key
        )

        return (
            value is not None
            and value < 1000
        )

    # Historical abnormality contributes no risk when unavailable.
    abnormality_component = (
        (
            deviation
            / 100
        )
        if deviation is not None
        else 0.0
    )

    components = {
        "thermal_severity":
            min(
                1,
                event[
                    "max_frp"
                ]
                / 140,
            ),

        "persistence":
            min(
                1,
                event[
                    "duration_hours"
                ]
                / 20,
            ),

        "industrial_proximity":
            float(
                nearby(
                    "distance_to_industrial_m"
                )
            ),

        "residential_proximity":
            float(
                nearby(
                    "distance_to_residential_m"
                )
            ),

        "infrastructure_exposure":
            float(
                nearby(
                    "distance_to_powerplant_m"
                )
                or nearby(
                    "distance_to_refinery_m"
                )
            ),

        "classification_context":
            float(
                event.get(
                    "classification",
                    {},
                ).get(
                    "predicted_class"
                )
                == "industrial_fire"
            ),

        "historical_abnormality":
            abnormality_component,
    }

    factors = {
        key:
            value
            * max(
                0,
                settings.risk_weights.get(
                    key,
                    0,
                ),
            )

        for key, value
        in components.items()
    }

    score = round(
        min(
            100,
            sum(
                factors.values()
            ),
        )
    )

    # --------------------------------------------------------
    # Risk level
    # --------------------------------------------------------

    if score <= 30:
        risk_level = (
            "Normal"
        )

    elif score <= 60:
        risk_level = (
            "Medium"
        )

    elif score <= 80:
        risk_level = (
            "High"
        )

    else:
        risk_level = (
            "Critical"
        )

    missing_context = [
        key
        for key in [
            "distance_to_industrial_m",
            "distance_to_residential_m",
            "ndvi",
        ]
        if context.get(key) is None
    ]

    return {
        "risk_score":
            score,

        "risk_level":
            risk_level,

        "risk_factors":
            factors,

        "method":
            (
                "Configurable decision-support scoring model; "
                "not scientifically validated"
            ),

        "missing_context":
            missing_context,

        "abnormality":
            abnormality,
    }