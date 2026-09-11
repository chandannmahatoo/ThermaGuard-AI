"""
Read-only validation of data/review_candidates.csv.

Checks duplicates, invalid labels/reviewed values, demo contamination,
incomplete reviewed rows, split-group consistency, feature-column
presence and training readiness against the exact contract in
app/ml.py. Never assigns labels and never marks rows reviewed.

Usage (from the repository root):
    PYTHONPATH=backend ./.venv/bin/python backend/validate_review_candidates.py
"""

from app import ml
from app.intelligence import CLASSES


def main():
    report = ml.candidate_report()

    print("=" * 44)
    print("THERMAGUARD REVIEW CANDIDATES VALIDATION")
    print("=" * 44)

    if not report["candidates_file"]:
        for problem in report["problems"]:
            print(f"PROBLEM: {problem}")

        print()
        print("Training ready: NO")
        raise SystemExit(1)

    print()
    print(f"Reviewed rows: {report['reviewed_rows']}")

    print(
        f"Eligible rows: {report['eligible_rows']}"
    )

    print(
        f"Classes present: "
        f"{report['classes_present']}/"
        f"{report['classes_total']}"
    )

    print(f"Split groups: {report['split_groups']}")

    print(
        f"Training ready: "
        f"{'YES' if report['training_ready'] else 'NO'}"
    )

    missing = report.get("missing") or []

    if missing:
        print()
        print("Missing:")

        for item in missing:
            print(f"- {item}")

    problems = report.get("problems") or []

    if problems:
        print()
        print("Problems:")

        for problem in problems:
            print(f"- {problem}")

    extra = report.get(
        "extra_columns_ignored"
    ) or []

    if extra:
        print()
        print(
            "Extra non-training columns "
            "(ignored by ml.py): "
            + ", ".join(extra)
        )

    print()
    print(
        f"Target classes: {', '.join(CLASSES)}"
    )

    if report["training_ready"]:
        print()
        print(
            "Next: run finalize_reviewed_labels.py "
            "to publish data/reviewed_labels.csv"
        )

    raise SystemExit(
        0 if report["training_ready"] else 1
    )


if __name__ == "__main__":
    main()
