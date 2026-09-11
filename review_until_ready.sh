#!/bin/bash

set -e

PROJECT="/Users/chandankumarmahato/Desktop/SIH2026"
PY="$PROJECT/.venv/bin/python"

cd "$PROJECT"

while true; do
    echo
    echo "=========================================="
    echo "CURRENT REVIEW STATUS"
    echo "=========================================="

    PYTHONPATH=backend "$PY" backend/review_progress.py

    if PYTHONPATH=backend "$PY" backend/validate_review_candidates.py >/tmp/tg_validation.txt 2>&1; then
        cat /tmp/tg_validation.txt

        echo
        echo "=========================================="
        echo "TRAINING DATA IS READY"
        echo "=========================================="
        break
    fi

    cat /tmp/tg_validation.txt

    echo
    echo "=========================================="
    echo "NEXT UNREVIEWED CANDIDATES"
    echo "=========================================="

    PYTHONPATH=backend "$PY" backend/review_queue.py --limit 5

    echo
    read -r -p "Paste event_id to review, or type QUIT: " EVENT_ID

    if [[ "$EVENT_ID" == "QUIT" || "$EVENT_ID" == "quit" ]]; then
        exit 0
    fi

    echo
    PYTHONPATH=backend "$PY" \
        backend/prepare_review_row.py "$EVENT_ID"

    echo
    echo "Allowed labels:"
    echo "1. industrial_fire"
    echo "2. persistent_industrial_thermal_source"
    echo "3. agricultural_vegetation_fire"
    echo "4. natural_thermal_event"
    echo "5. possible_false_positive"
    echo

    read -r -p "Enter VERIFIED label or SKIP: " LABEL

    if [[ "$LABEL" == "SKIP" || "$LABEL" == "skip" ]]; then
        continue
    fi

    case "$LABEL" in
        industrial_fire|persistent_industrial_thermal_source|agricultural_vegetation_fire|natural_thermal_event|possible_false_positive)
            ;;
        *)
            echo "Invalid class."
            continue
            ;;
    esac

    read -r -p "Enter genuine split_group: " GROUP
    read -r -p "Enter real source reference/evidence: " SOURCE

    if [[ -z "$GROUP" || -z "$SOURCE" ]]; then
        echo "Missing group/source. Review not saved."
        continue
    fi

    echo
    echo "Event: $EVENT_ID"
    echo "Label: $LABEL"
    echo "Group: $GROUP"
    echo "Source: $SOURCE"
    echo

    read -r -p "Type YES only if you personally verified this label: " CONFIRM

    if [[ "$CONFIRM" != "YES" ]]; then
        echo "Not saved."
        continue
    fi

    PYTHONPATH=backend "$PY" \
        backend/prepare_review_row.py "$EVENT_ID" \
        --label "$LABEL" \
        --split-group "$GROUP" \
        --reviewer PRAGYAX_review \
        --source-reference "$SOURCE" \
        --reviewed true
done

echo
echo "Finalizing reviewed labels..."

PYTHONPATH=backend "$PY" \
    backend/finalize_reviewed_labels.py

echo
echo "Final status:"

PYTHONPATH=backend "$PY" \
    backend/review_progress.py
