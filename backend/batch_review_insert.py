from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"

SOURCE = (
    "NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/map/index.html ; "
    "project FIRMS observation and stored geospatial context reviewed"
)

REVIEWER = "PRAGYAX_review"

ALLOWED_LABELS = {
    "industrial_fire",
    "persistent_industrial_thermal_source",
    "agricultural_vegetation_fire",
    "natural_thermal_event",
    "possible_false_positive",
}


# ============================================================
# ADD YOUR REVIEWED DATA HERE
# Format:
# ("EVENT_ID", "LABEL", "SPLIT_GROUP"),
# ============================================================

"""
"industrial_fire"
"persistent_industrial_thermal_source"
"agricultural_vegetation_fire"
"natural_thermal_event"
"possible_false_positive"
"""

REVIEWS = [
    (
        "TG-firms-484050869f0b38f9404f",
        "industrial_fire",
        "hazira_aug_2026",
    ),
    (
        "TG-firms-067b7987b61e0a46c33d",
        "industrial_fire",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-1a74190a4abd22ccee76",
        "persistent_industrial_thermal_source",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-439758d35ce9920ad43e",
        "persistent_industrial_thermal_source",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-59781240d8e0ae0f3170",
        "agricultural_vegetation_fire",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-870b462a74eed7e91086",
        "agricultural_vegetation_fire",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-fd17266b4d6fdaaa1026",
       "natural_thermal_event",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-67b1a7dc95a8e01f5d5c",
        "natural_thermal_event",
        "punjab_plains_sep_2026",
    ),
    (
        "TG-firms-1a552a72d32d2aa6ff08",
        "possible_false_positive",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-28cdedb033f322e8c576",
        "possible_false_positive",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-3297f9d156835a0a1537",
        "possible_false_positive",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-34beb5f4914d6766742b",
        "natural_thermal_event",
        "angul_talcher_sep_2026",
    ),
    (
        "TG-firms-354f64e5836d2a13c442",
        "agricultural_vegetation_fire",
        "chandrapur_sep_2026",
    ),
    (
        "TG-firms-eb7aff5b08219fa0be97",
        "agricultural_vegetation_fire",
        "chandrapur_sep_2026",
    ),
    (
        "TG-firms-3397d3c737eba55ac004",
        "industrial_fire",
        "unmapped_sep_2026",
    ),
    (
        "TG-firms-ee98742f57357bb34854",
        "industrial_fire",
        "unmapped_sep_2026",
    ),
]


def insert_review(event_id: str, label: str, group: str) -> bool:
    if label not in ALLOWED_LABELS:
        print(f"❌ INVALID LABEL: {label}")
        return False

    if not event_id.strip():
        print("❌ Missing event_id")
        return False

    if not group.strip():
        print(f"❌ Missing split group for {event_id}")
        return False

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")

    cmd = [
        str(PYTHON),
        str(ROOT / "backend" / "prepare_review_row.py"),
        event_id,
        "--label",
        label,
        "--split-group",
        group,
        "--reviewer",
        REVIEWER,
        "--source-reference",
        SOURCE,
        "--reviewed",
        "true",
    ]

    print()
    print("=" * 75)
    print(f"EVENT : {event_id}")
    print(f"LABEL : {label}")
    print(f"GROUP : {group}")
    print("=" * 75)

    result = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
    )

    if result.returncode == 0:
        print(f"✅ SAVED: {event_id}")
        return True

    print(f"❌ FAILED: {event_id}")
    return False


def run_status():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")

    print()
    print("=" * 75)
    print("REVIEW PROGRESS")
    print("=" * 75)

    progress = subprocess.run(
        [
            str(PYTHON),
            str(ROOT / "backend" / "review_progress.py"),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    print(progress.stdout)

    print()
    print("=" * 75)
    print("VALIDATION")
    print("=" * 75)

    validation = subprocess.run(
        [
            str(PYTHON),
            str(ROOT / "backend" / "validate_review_candidates.py"),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    print(validation.stdout)

    return progress.stdout


def finalize():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")

    print()
    print("=" * 75)
    print("FINALIZING REVIEWED LABELS")
    print("=" * 75)

    subprocess.run(
        [
            str(PYTHON),
            str(ROOT / "backend" / "finalize_reviewed_labels.py"),
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )


def main():
    if not REVIEWS:
        print("No review rows configured.")
        print("Add tuples inside REVIEWS first.")
        return

    print(f"Starting batch insertion for {len(REVIEWS)} events")

    success = 0
    failed = 0

    for index, (event_id, label, group) in enumerate(
        REVIEWS,
        start=1,
    ):
        print()
        print(f"[{index}/{len(REVIEWS)}]")

        if insert_review(event_id, label, group):
            success += 1
        else:
            failed += 1

    print()
    print("=" * 75)
    print("BATCH COMPLETE")
    print("=" * 75)
    print(f"Successful: {success}")
    print(f"Failed:     {failed}")

    status = run_status()

    if "Training ready: YES" in status:
        print()
        print("✅ TRAINING GATE PASSED")
        finalize()

        print()
        print("✅ reviewed_labels.csv finalized.")
    else:
        print()
        print("⚠️ Training gate not reached yet.")
        print("reviewed_labels.csv was NOT automatically finalized.")


if __name__ == "__main__":
    main()