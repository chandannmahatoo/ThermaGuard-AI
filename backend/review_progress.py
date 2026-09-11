"""Read-only human-review progress using the existing ML eligibility and gate."""
import argparse
from collections import Counter
from pathlib import Path
import sys

from app import ml
from app.intelligence import CLASSES
from review_common import read_csv


def review_progress(path=None):
    path = Path(path) if path is not None else ml.CANDIDATES
    _, rows, _ = read_csv(path)
    report = ml.candidate_report(path)
    eligible = ml.dataset(path)
    counts = Counter(row['label'] for row in eligible)
    return {**report, 'total_candidates': len(rows),
            'class_counts': {label: counts[label] for label in CLASSES},
            'missing_classes': [label for label in CLASSES if not counts[label]],
            'remaining_rows': max(0, 30 - len(eligible)),
            'remaining_groups': max(0, 10 - report['split_groups']),
            'row_completion_percent': min(100, len(eligible) / 30 * 100)}


def render_progress(report):
    lines = [f"Total candidates: {report['total_candidates']}",
             f"Reviewed rows: {report['reviewed_rows']}",
             f"Eligible rows: {report['eligible_rows']}", 'Required minimum: 30',
             f"Remaining reviewed events needed: {report['remaining_rows']}", '',
             'Class distribution (eligible rows only):']
    lines.extend(f"{label}: {count}" for label, count in report['class_counts'].items())
    lines.extend(['', f"Classes present: {report['classes_present']}/5",
                  'Missing classes: ' + (', '.join(report['missing_classes']) or 'None'),
                  f"Split groups: {report['split_groups']}/10",
                  f"Remaining independent groups needed: {report['remaining_groups']}",
                  f"Eligible-row completion: {report['row_completion_percent']:.1f}% (30-row target only)",
                  f"Training ready: {'YES' if report['training_ready'] else 'NO'}",
                  'This is candidate readiness, not a trained model or publication of reviewed_labels.csv.',
                  'Group independence and source authenticity require human verification.'])
    if report['problems']:
        lines.append('Validation problems (resolve before finalization):')
        lines.extend(f'- {problem}' for problem in report['problems'])
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, default=ml.CANDIDATES)
    args = parser.parse_args(argv)
    try:
        print(render_progress(review_progress(args.candidates)))
        return 0  # A valid progress report is successful even when not training-ready.
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
