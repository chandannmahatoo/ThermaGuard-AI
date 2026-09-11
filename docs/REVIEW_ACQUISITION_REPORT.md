# ThermaGuard AI — real candidate expansion report

Verified September 11, 2026. Expanded the pool from **13 to 33 real events**, within
the requested 30–50 range. No labels or approvals were generated and no training occurred.

## Real data

- **69 new unique FIRMS observations** stored, giving **121 real detections** total.
- **102 validated observation rows returned** across two network-enabled passes;
  33 were repeat observations and were deduplicated. Zero validation rejections
  occurred in successfully returned responses.
- 30 network-enabled requests: 29 returned responses; one network failure was
  retried successfully in the second pass. A separate initial sandbox attempt
  made 12 failed requests and stored nothing.
- **20 new events**, zero removed/reidentified events, **33 candidates** total.
- All acquisitions used **VIIRS_SNPP_NRT**, stored satellite `N` / instrument `VIIRS`.
- New periods: **August 10, September 5 and September 8, 2026**. Combined candidate
  dates: **August 5–September 10, 2026** (UTC).
- **Zero alerts created** during acquisition. Existing successful OSM/Copernicus
  context was preserved. New historical events have explicit unavailable context;
  no enrichment or incident details were fabricated.

| Queried region | Requests | Returned rows | New detections | New events |
|---|---:|---:|---:|---:|
| jamnagar | 5 | 0 | 0 | 0 |
| korba | 5 | 4 | 2 | 2 |
| angul_talcher | 5 | 87 | 61 | 12 |
| chandrapur | 5 | 8 | 4 | 4 |
| punjab_plains | 5 | 3 | 2 | 2 |
| central_madhya_pradesh | 5 | 0 | 0 | 0 |

Returned-row totals exclude the unmeasurable failed response; they do not assert
that response contained zero observations. Jamnagar and central Madhya Pradesh
returned no detections in the successful queried windows. The second pass exhausted
the plan at 33 candidates; its internal target of 40 was not reached. Collection
stopped within the user's requested range.

Current representation: Hazira **11**, Angul–Talcher **12**, Chandrapur **4**,
Korba **2**, Punjab plains **2**, plus **2 existing Gujarat events outside the
configured search-zone map**. Five named search zones are represented. These zone
counts do not establish five independent scientific training groups.

## Human review and model

| Measure | Verified value |
|---|---:|
| Reviewed candidates | 1 |
| Eligible reviewed candidates | 1 |
| Unreviewed candidates | 32 |
| Classes represented | 1 / 5 |
| Human split groups | 1 / 10 |
| Training ready | false |
| Model available | false |
| Training performed | **No** |

Eligible class counts: `persistent_industrial_thermal_source = 1`;
`industrial_fire = 0`; `agricultural_vegetation_fire = 0`;
`natural_thermal_event = 0`; `possible_false_positive = 0`.

The published training dataset remains absent; `ml.status()` therefore reports
zero published eligible rows, while the candidate validator reports one eligible
candidate. These are different inputs. The gate remains 30 eligible human-reviewed
non-demo events, all five classes, and ten genuinely independent split groups.

The complete candidate row for **TG-firms-12a727a697efdb9146a2** was compared to the
pre-acquisition backup and is **exactly unchanged**, including its human fields and
any custom columns. The full stored event payload passed the transaction guard
throughout acquisition. Its group remains `hazira_sep_2026`. **No event-ID
reconciliation or label transfer was needed.**

## Files created

- `backend/acquire_review_candidates.py`: plan parsing, real-only ingestion,
  bounded provider requests, review backups, transactional evidence guard, no alerts.
- `backend/candidate_inventory.py`: read-only geographic/date inventory and cohort suggestions.
- `backend/review_queue.py`: chronological filtering without predicted-class ranking.
- `backend/export_review_packets.py`: neutral stored-evidence packets and unverified search aids.
- `backend/app/review_validation.py`: shared source-reference syntax guard.
- `backend/tests/test_candidate_acquisition.py`: 43 additional isolated test cases.
- `data/review_acquisition_plan.example.json` and `data/review_acquisition_plan.json`.
- `data/review_packets/`: **32 Markdown packets**, plus `index.json`.
- `data/review_acquisition_last_run.json`, archived pass reports, byte-for-byte CSV
  backups and reviewed-row snapshots under `data/backups/`.
- `docs/REVIEW_ACQUISITION.md` and this report.

## Files modified in this task

- `backend/app/main.py`: optional deferred commit for transaction-safe pipeline reuse.
- `backend/app/ml.py`: stronger reference and metadata eligibility checks; unchanged feature list/gate.
- `backend/review_common.py`: shared source-reference guard for explicit approval/publication.
- `backend/export_review_candidates.py`: refuse disappearance of reviewed event IDs.
- `backend/tests/test_system.py` and `backend/tests/test_review_workflow.py`: replace
  obsolete placeholder success fixtures with example-domain test references;
  retain unreviewed removal coverage and add reviewed-removal refusal coverage.
- `data/review_candidates.csv`: real new candidates; existing reviewed row preserved.
- `README.md`, `docs/DATA.md`, `docs/MODEL.md`: acquisition and grouping documentation.
- Configured SQLite database: 69 new real detections and 20 new real events.

Other pre-existing repository modifications were retained. No `.env`, model
artifact, or published reviewed-label file was changed.

## Verification

**115 tests passed**, with two existing Starlette dependency deprecation warnings.
Tests ran successfully before any real acquisition and again after final changes.
Coverage includes plan/date/bounds validation, raw-provenance checking, real-only
operation, deduplication, alert suppression, rollback for reviewed ID/evidence
changes, exact manual/custom-note preservation, exporter idempotency, source
placeholder rejection, packet neutrality, inventory/queue/cohort behavior, no
review-only feature leakage, and the unchanged training gate. No classifier was trained.

The exporter, inventory, progress report, validator, queue and packet exporter were
run on the resulting real data. Final CSV export was a byte-identical no-op. The
validator exited 1 because training readiness is false; it reported no data
validation problems. The packet manifest lists exactly 32 current unreviewed files.

## Inspect the next five events

These exact commands display evidence without changing review fields:

```sh
cd /Users/chandankumarmahato/Desktop/SIH2026
PYTHONPATH=backend ./.venv/bin/python backend/review_queue.py --limit 5

for event_id in \
  TG-firms-17a1d9abb72d51592396 \
  TG-firms-4ee5757a7f0de593d158 \
  TG-firms-2cccb1d15213eca9a6c1 \
  TG-firms-889ac864d33ccc099b73 \
  TG-firms-b21337d75f2e1696a2f7
do
  PYTHONPATH=backend ./.venv/bin/python backend/prepare_review_row.py "$event_id"
done
```

For each event, verify the corresponding packet and independent sources before
using explicit approval flags. The command above does not select a label, create a
reference, or mark anything reviewed. Full approval and grouping guidance is in
[REVIEW_ACQUISITION.md](REVIEW_ACQUISITION.md).
