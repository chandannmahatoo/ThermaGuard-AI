# Real candidate acquisition and human review

Candidate count is not eligible reviewed count. Acquisition never labels, approves,
finalizes reviewed labels, trains, or sends alerts. Every region is only a search
zone. Industrial or vegetation context does not establish an event class.

## Audit before this expansion (2026-09-11)

The database contained 52 real NASA FIRMS VIIRS observations and 13 events. Eleven
events were concentrated around Hazira (approximately 21.104 N, 72.644 E), including
ten August historical events. The other two were at 22.92957 N, 70.10769 E and
23.10672 N, 72.22006 E. Observation dates spanned August 5–September 10, 2026.
All stored sensor pairs were satellite `N`, instrument `VIIRS`.

The approved event `TG-firms-12a727a697efdb9146a2` had one human label,
`persistent_industrial_thermal_source`, and split group `hazira_sep_2026`.
It remained eligible under the strengthened source-reference syntax guard.
No reviewed dataset had been published and no trained model was available.

Historical observations are real candidate evidence. They are not independently
reviewed examples until a human reviews the resulting events. The existing
single-link clustering joins observations within the configured 2 km / 24 hours;
chains can span longer intervals. Event IDs derive from the earliest sorted
observation. Adding an earlier observation or a bridge can merge events and change
IDs. Additional nearby history can also change baseline features without changing
an ID. Both cases matter to an existing approved evidence snapshot.

## Commands

Run from the repository root using its existing virtual environment:

```sh
PYTHONPATH=backend ./.venv/bin/python backend/acquire_review_candidates.py --plan data/review_acquisition_plan.json --dry-run
PYTHONPATH=backend ./.venv/bin/python backend/acquire_review_candidates.py --plan data/review_acquisition_plan.json --no-alert
PYTHONPATH=backend ./.venv/bin/python backend/export_review_candidates.py
PYTHONPATH=backend ./.venv/bin/python backend/candidate_inventory.py
PYTHONPATH=backend ./.venv/bin/python backend/review_queue.py --limit 5
PYTHONPATH=backend ./.venv/bin/python backend/review_progress.py
PYTHONPATH=backend ./.venv/bin/python backend/validate_review_candidates.py
PYTHONPATH=backend ./.venv/bin/python backend/export_review_packets.py
```

The validator exits 1 while the gate is closed; that is an expected readiness
result. Dry-run validates the plan and prints the number of requests without
contacting providers or changing files. A single region can instead be specified
with `--region`, `--bounds WEST SOUTH EAST NORTH`, `--start-date`, `--end-date`,
`--source`, and `--max-observations`.

The example plan includes Hazira/Surat, Jamnagar, Korba, Angul–Talcher,
Chandrapur, Punjab plains and central Madhya Pradesh. The first working plan
excludes new Hazira queries to protect its existing review. Plans include August
and September periods, subject to source availability. Search results may be
empty: a search-zone name does not establish that detections or incidents exist.

[NASA FIRMS Area API](https://firms.modaps.eosdis.nasa.gov/api/area/) accepts windows
of 1–5 days and starts a dated window on the supplied date. The tool chunks longer
ranges accordingly, never exceeds the configured provider observation budget,
and skips whole responses exceeding a region's plan budget. It does not truncate
observations into partial clusters. The target is checked between complete
responses, so a final response can take the count above the target. Use smaller
regions/date windows if necessary. No class-based sampling is performed.
Check [source availability](https://firms.modaps.eosdis.nasa.gov/api/data_availability/)
when planning older periods; NRT and standard products have different coverage.

## Review safety and operational limits

Before acquisition, `data/backups/` receives a byte-for-byte candidate CSV backup
and a JSON snapshot of every reviewed row, including custom columns and notes.
The tool checks the CSV evidence against the database, then reuses `process()`
with `enrich=False`, `create_notifications=False`, and `commit=False`. Existing
successful OSM/Copernicus context is retained; new historical candidates explicitly
show missing enrichment. Raw FIRMS rows, timestamps and provider metadata remain
in each detection. New detections also record the query source, bounds and period.

Every approved event's full stored payload must remain identical before commit.
A changed ID, merged membership, new baseline or changed context causes rollback
of that batch. No heuristic label transfer is attempted. Earlier successful
batches remain committed. Human reconciliation is required if a protected event
changes; the tool does not reopen reviews automatically. The standalone exporter
also refuses to silently remove reviewed IDs.

Each committed batch is exported and its reviewed rows are compared exactly
with the initial snapshot. `review_acquisition_last_run.json` contains per-request
counts and outcomes without credentials. Null raw/rejected counts mean the
provider response could not be measured, not zero observations. Accepted counts
mean provider validation passed; new-detection counts describe actual storage.
Duplicates do not increase stored counts. Network errors never echo request URLs.

Use one acquisition/editor/sync writer at a time. CSV replacement is atomic and
checks for intervening edits, but SQLite and CSV cannot share a single atomic
commit. If the process is interrupted after DB commit and before CSV export,
rerun the exporter; the prior CSV backup preserves human work. Resolve a reviewed
snapshot conflict explicitly rather than bypassing the guard. Backups contain
human reviewer metadata and should receive the same access controls as the CSV.

## Cohort strategy and queue

Inventory derives `suggested_cohort` from the event centroid's named search zone
and UTC start month, for example `hazira_sep_2026`. It does not write that value to
`split_group`. Events within the same zone/month normally share a name. Overlapping
search zones receive a deterministic combined name. Unmapped coordinates are
reported as unmapped and require a meaningful geographic assignment by a human.

A month boundary does not prove independence. A persistent facility observed in
multiple months, nearby sites within the baseline radius, or events linked to one
incident may need the same split group across months to avoid leakage. Reviewers
must merge such dependent cohorts, not invent unique per-event groups to satisfy
the gate. Broad search zones may also need better geographic definitions before
training. Region names, coordinates and suggestions never join the ML feature list.

The queue orders by date, region and event ID, with no predicted-class ordering:

```sh
PYTHONPATH=backend ./.venv/bin/python backend/review_queue.py --limit 5 --region korba
PYTHONPATH=backend ./.venv/bin/python backend/review_queue.py --cohort hazira_aug_2026 --reviewed false
PYTHONPATH=backend ./.venv/bin/python backend/review_queue.py --start-date 2026-08-01 --end-date 2026-08-31 --landuse industrial
```

Use `--date YYYY-MM-DD` for one UTC date or `--reviewed true|false|all` to change
the review-state filter. These commands never change the CSV.

## Packets and approval

`data/review_packets/index.json` lists current unreviewed packets. Packet Markdown
includes stored thermal aggregates, historical baselines, abnormality, OSM context,
facility names, NDVI acquisition date, risk and source sensors. Search/map links
are explicitly unverified aids. Missing enrichment remains unavailable. Packets
contain no model predictions, class probabilities, or recommended label. Treat
packets as generated files; keep human notes in custom CSV columns or separate
files. Old packets may remain on disk but are excluded from the current index.

Inspect an event with `prepare_review_row.py EVENT_ID` without flags. This is
read-only. Only after checking the packet and independent evidence should a human
supply `--label`, `--reviewer`, `--source-reference`, `--split-group`, and explicit
`--reviewed true` to that helper. No example approved reference is supplied here.

The reference syntax guard rejects empty/short meaningless strings and obvious
placeholders such as TODO, TBD, test, N/A, placeholder, and
REAL_SOURCE_OR_EVIDENCE_HERE. A URL is not mandatory and no domain allowlist is
used. Passing syntax checks does not authenticate evidence or approve the label.

The gate remains **at least 30 eligible reviewed non-demo events, all five classes,
and at least 10 genuinely independent split groups**. This workflow never trains,
even if the candidate count passes 30 or the gate later opens.
