from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data" / "review_candidates.csv"
PYTHON = ROOT / ".venv" / "bin" / "python"

ALLOWED = {
    "industrial_fire",
    "persistent_industrial_thermal_source",
    "agricultural_vegetation_fire",
    "natural_thermal_event",
    "possible_false_positive",
}


def value(row, name):
    v = row.get(name)
    return None if pd.isna(v) else v


def suggest(row):
    industrial = value(row, "distance_to_industrial_m")
    factory = value(row, "distance_to_factory_m")
    farmland = value(row, "distance_to_farmland_m")
    forest = value(row, "distance_to_forest_m")

    recurrence = value(row, "recurrence_count") or 0
    persistence = value(row, "persistence_days") or 0
    detections = value(row, "detection_count") or 0
    max_frp = value(row, "max_frp") or 0

    landuse = str(value(row, "landuse_class") or "").lower()

    if recurrence >= 2 and (
        (industrial is not None and industrial <= 500)
        or (factory is not None and factory <= 500)
        or landuse == "industrial"
    ):
        return "persistent_industrial_thermal_source"

    if (
        "farm" in landuse
        or "agric" in landuse
        or (farmland is not None and farmland <= 500)
    ):
        return "agricultural_vegetation_fire"

    if forest is not None and forest <= 500:
        return "natural_thermal_event"

    if (
        detections <= 1
        and recurrence == 0
        and persistence <= 1
        and max_frp < 3
        and industrial is None
        and farmland is None
        and forest is None
    ):
        return "possible_false_positive"

    return None


def group_for(row):
    existing = value(row, "split_group")
    if existing:
        return str(existing)

    region = str(value(row, "region") or "").strip().lower()
    start = value(row, "start_time")
    lat = value(row, "latitude")
    lon = value(row, "longitude")

    try:
        dt = pd.to_datetime(start)
        month_year = dt.strftime("%b_%Y").lower()
    except Exception:
        month_year = "unknown_date"

    if region:
        return f"{region}_{month_year}"

    # Coordinate-based known project regions
    if lat is not None and lon is not None:
        lat = float(lat)
        lon = float(lon)

        # Hazira
        if 21.00 <= lat <= 21.20 and 72.55 <= lon <= 72.75:
            return f"hazira_{month_year}"

        # Angul-Talcher
        if 20.70 <= lat <= 21.10 and 84.70 <= lon <= 85.20:
            return f"angul_talcher_{month_year}"

        # Korba
        if 22.20 <= lat <= 22.60 and 82.40 <= lon <= 82.90:
            return f"korba_{month_year}"

        # Chandrapur
        if 19.60 <= lat <= 20.20 and 79.00 <= lon <= 79.60:
            return f"chandrapur_{month_year}"

        # Punjab
        if 30.50 <= lat <= 32.00 and 74.50 <= lon <= 76.50:
            return f"punjab_{month_year}"

        # Gujarat / Ahmedabad region
        if 22.50 <= lat <= 23.50 and 71.50 <= lon <= 73.50:
            return f"gujarat_{month_year}"

    return None


def source_for(row):
    lat = value(row, "latitude")
    lon = value(row, "longitude")
    recurrence = value(row, "recurrence_count")
    landuse = value(row, "landuse_class")

    parts = [
        "NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/map/index.html"
    ]

    if lat is not None and lon is not None:
        parts.append(f"coordinates={lat},{lon}")

    if landuse:
        parts.append(f"stored OSM landuse={landuse}")

    if recurrence is not None:
        parts.append(f"stored recurrence_count={recurrence}")

    return " ; ".join(parts)


def save(event_id, label, group, source):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")

    subprocess.run(
        [
            str(PYTHON),
            str(ROOT / "backend" / "prepare_review_row.py"),
            event_id,
            "--label", label,
            "--split-group", group,
            "--reviewer", "PRAGYAX_review",
            "--source-reference", source,
            "--reviewed", "true",
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )


def main():
    df = pd.read_csv(CSV)

    reviewed = df["reviewed"].astype(str).str.lower().eq("true")
    rows = df[~reviewed]

    print(f"Unreviewed candidates: {len(rows)}")

    for _, row in rows.iterrows():
        event_id = str(row["event_id"])
        label = suggest(row)
        group = group_for(row)
        source = source_for(row)

        print("\n" + "=" * 70)
        print("EVENT:", event_id)
        print("Suggested label:", label or "AMBIGUOUS")
        print("Suggested group:", group)
        print("Source:", source)
        print("Recurrence:", value(row, "recurrence_count"))
        print("Landuse:", value(row, "landuse_class"))
        print("Risk:", value(row, "risk_level"))

        if label is None or group is None:
            print("Skipped: insufficient evidence.")
            continue

        answer = input("Approve suggestion? [y/N/q]: ").strip().lower()

        if answer == "q":
            break

        if answer != "y":
            print("Skipped.")
            continue

        confirm = input("Type YES to record as reviewed: ").strip()

        if confirm != "YES":
            print("Not recorded.")
            continue

        save(event_id, label, group, source)
        print("Saved:", event_id)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")

    print("\nREVIEW PROGRESS")
    subprocess.run(
        [str(PYTHON), str(ROOT / "backend" / "review_progress.py")],
        cwd=ROOT,
        env=env,
    )

    print("\nVALIDATION")
    subprocess.run(
        [str(PYTHON), str(ROOT / "backend" / "validate_review_candidates.py")],
        cwd=ROOT,
        env=env,
    )


if __name__ == "__main__":
    main()