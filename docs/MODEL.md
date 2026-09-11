# Model and risk

One `features(event)` function is shared by training and inference. Version 2 uses thermal aggregates and sensor quality, duration/counts/day-night behavior, spread and persistence, historical recurrence/frequency/FRP statistics, seven OSM distances, facility counts, NDVI/fractions and available land-use indicators. Real NDVI comes only from the Copernicus adapter in real mode; in demo mode it stays missing. Missing context stays missing and is imputed within the fitted training pipeline. Raw coordinates are excluded to reduce geographic memorization.

Classes: industrial_fire, persistent_industrial_thermal_source, agricultural_vegetation_fire, natural_thermal_event, possible_false_positive. No rule-based guess is presented as an ML class when a model does not exist.

Reviewed input has one row per event with label, reviewer, traceable source and independent `split_group` (prefer region/time cohorts). Only `reviewed=true` and `is_demo=false` rows qualify. Duplicate event IDs are rejected. The candidate export (`backend/export_review_candidates.py`), validator (`backend/validate_review_candidates.py`) and finalizer (`backend/finalize_reviewed_labels.py`) enforce this same contract; the training pipeline reads exactly the review columns plus the feature schema, so reviewer-assistance columns can never enter the model. The pipeline uses independent group train/validation/test splits, median imputation fitted on train only, and a 200-tree balanced Random Forest with fixed seeds. All classes must occur in every split. Hyperparameters are fixed; validation is reported, not repeatedly optimized against test.

Saved artifacts use joblib and include a separate feature schema, version and genuine validation/test accuracy, balanced accuracy, macro precision/recall/F1, per-class report and confusion matrix. Only locally trusted artifacts should be loaded. Model evaluation quality depends on reviewer quality and independent split-group design; the minimum row gate alone does not establish adequacy.

Historical abnormality is separate from classification: earlier nearby real events (or earlier demo events within demo mode) provide baselines for mean FRP, brightness, detection frequency, spread and duration. Without a baseline, scores/status explicitly say unavailable. The current heuristic flags ratios above 1.5; it is not a validated anomaly detector.

Risk adds bounded thermal severity (50 points), persistence (10), industrial proximity (10), residential proximity (10), infrastructure exposure (5), trained industrial-fire class context (5), and historical deviation (up to 10) — a canonical total of exactly 100. Thresholds: 0–30 Normal, 31–60 Medium, 61–80 High, 81–100 Critical. Automatic alerts trigger at or above the configured threshold. Missing context contributes zero and is disclosed; without OSM context a context-free event can score at most 60 (Medium), which is deliberate honesty about unknown proximity rather than a hidden penalty. Risk is a decision-support heuristic, never model confidence.

Weights are configurable through the server-side JSON RISK_WEIGHTS setting and validated at startup: all seven keys are required, negative values and unknown keys are rejected, and the total must equal exactly 100 — an invalid configuration prevents boot instead of being silently clamped. The demo fixture seeds an alert threshold of 60 and a Medium minimum alert level so threshold alerting stays demonstrable on the corrected scale. The administrator alert threshold is stored in SQLite and can be changed in Administration. Initial state: training blocked, model absent, no metrics. Satellite NDVI is available in real mode with Copernicus credentials; demo events never trigger satellite requests.

## Human-review CSV contract (audited against feature version 2)

The canonical training header has **38 columns**: the seven metadata columns below, followed by the 31 features in the stated order. Current candidates have **50 columns**: that same header followed by 12 assistance columns. The header-only template in `data/templates/reviewed_labels.csv` is the authoritative ordered example.

Metadata order:

```text
event_id,split_group,label,reviewed,reviewer,source_reference,is_demo
```

ML feature order:

```text
mean_frp,max_frp,mean_brightness,max_brightness,quality_mean,duration_hours,detection_count,night_fraction,spatial_spread_km,persistence_days,detection_frequency,recurrence_count,historical_mean_frp,historical_max_frp,historical_std_frp,historical_baseline_available,distance_to_industrial_m,distance_to_refinery_m,distance_to_powerplant_m,distance_to_factory_m,distance_to_forest_m,distance_to_farmland_m,distance_to_residential_m,nearby_industrial_count,nearby_facility_count,ndvi,vegetation_fraction,built_up_fraction,landuse_industrial,landuse_forest,landuse_farmland
```

Review-only assistance order:

```text
latitude,longitude,start_time,last_seen_time,landuse_class,osm_context_available,satellite_context_available,abnormality_score,abnormality_status,risk_score,risk_level,nearby_facility_names
```

Accepted labels are exactly `industrial_fire`, `persistent_industrial_thermal_source`, `agricultural_vegetation_fire`, `natural_thermal_event`, and `possible_false_positive`. No tool chooses a label or source reference. Facility proximity, persistence, NDVI and risk are evidence for consideration, not label rules.

Exact existing `ml.dataset()` eligibility behavior, preserved by this work:

- `reviewed.lower()` must equal `true`; `is_demo.lower()` must equal `false`. These checks do **not** trim whitespace. Other boolean spellings, `1`/`0`, empty flags and padded flags are ineligible.
- `label` must match an accepted label exactly (case-sensitive, no trimming).
- `event_id`, `reviewer`, `source_reference`, and `split_group` must be nonempty. The loader itself only tests string truthiness, so whitespace-only strings are a limitation; the new update/finalization guards reject them rather than relaxing the loader.
- Nonempty feature cells must convert to finite floats. Blank/missing numeric cells become `None`; a row with all features missing is rejected. Feature version 2's vector builder maps missing values to NaN, and the existing fitted median `SimpleImputer(add_indicator=True, keep_empty_features=True)` handles them. Boolean feature values should be numeric `0`/`1`, unlike the metadata flags.
- Duplicate **eligible** event IDs cause a loader error. The review tools additionally reject duplicate candidate IDs before changing any file.
- Extra CSV columns can be present in the loaded dictionaries, but only the ordered `FEATURES` whitelist reaches the vector. Coordinates, notes, reviewer identity, labels, risk and references cannot enter the feature vector. Finalization writes exactly `TRAINING_COLUMNS` and drops assistance/custom notes from the published file only.
- `split_group` has no geographic authenticity validator. The loader requires it to be nonempty; readiness counts distinct raw strings. The existing candidate validator detects a repeated event in different groups. Humans must establish independent region/time cohorts and avoid aliases or arbitrary groups created to pass the threshold. The new writer rejects padded group strings.
- The unchanged gate requires 30 eligible rows, all five classes, and 10 groups. Training then checks all five classes occur in each independent train/validation/test split. Reaching the minimum count does not guarantee those splits or adequate model quality.

`ml.candidate_report()` counts reviewed flags after trimming, while `ml.dataset()` does not; its counts can therefore differ on malformed CSVs. Its readiness field is the existing numeric/class/group gate, not a guarantee that every candidate has passed its diagnostic checks. Finalization refuses malformed flags, incomplete reviews, invalid feature values and missing canonical columns and cross-checks reviewed IDs with `ml.dataset()` before publication. The classifier, feature builder, APIs and gate are unchanged.

## Offline human-review commands

Run from the project root:

```sh
PYTHONPATH=backend ./.venv/bin/python backend/export_review_candidates.py
PYTHONPATH=backend ./.venv/bin/python backend/review_progress.py
PYTHONPATH=backend ./.venv/bin/python backend/review_event_summary.py EVENT_ID
PYTHONPATH=backend ./.venv/bin/python backend/prepare_review_row.py EVENT_ID
```

Summary/prepare without update flags are read-only, query stored non-demo events, and leave all seven checklist items unchecked. They do not call providers, Ollama, training or notification services. Missing evidence is printed as unavailable, not zero. Context acquisition date is shown so reviewers can judge temporal relevance.

After personally inspecting the evidence and collecting a real source reference, provide your own values:

```sh
PYTHONPATH=backend ./.venv/bin/python backend/prepare_review_row.py EVENT_ID \
  --label YOUR_CHOSEN_ACCEPTED_CLASS \
  --split-group YOUR_INDEPENDENT_REGION_TIME_COHORT \
  --reviewer YOUR_REVIEWER_ID \
  --source-reference 'YOUR_ACTUAL_EVIDENCE_REFERENCE' \
  --reviewed true
PYTHONPATH=backend ./.venv/bin/python backend/validate_review_candidates.py
PYTHONPATH=backend ./.venv/bin/python backend/review_progress.py
```

These uppercase tokens are placeholders to replace, not labels or evidence supplied by the system. Explicit updates require a reviewer and split group (existing values can satisfy these); reviewed=true also requires an accepted label and actual reference. Feature/provenance cells cannot be edited with this helper. Changing metadata on an approved row requires explicit `--reviewed true` to reapprove or `--reviewed false` to reopen.

Re-export preserves exact manual-field values (including intentional blanks), adds real events in event-ID order, and retains custom columns such as `review_notes`. Removed/reclustered rows leave the active candidate set but their entire original contents remain in the reported timestamped backup. No old review is transferred to a new event ID. If a previously complete, eligible reviewed snapshot's evidence changes, export refuses to overwrite it; the reviewer must explicitly reopen it before refreshing. Incomplete historical rows can acquire newly exported objective features while their human fields remain unchanged.

Every CSV replacement backs up the previous file under `data/backups/` and uses atomic replacement. Identical re-exports do not rewrite the file or create unnecessary backups. A changed-on-disk check catches intervening edits; this is a single-reviewer CLI workflow, not a concurrent editing/locking system. Backups contain human review work: preserve them securely, and never point the training loader at the backup directory.

When the validator genuinely reports readiness, publish deliberately:

```sh
PYTHONPATH=backend ./.venv/bin/python backend/finalize_reviewed_labels.py
```

Finalization may also publish fewer complete rows to save legitimate review progress, but it never changes the gate or trains. A previous published CSV is backed up before replacement. `review_progress.py` reports candidate readiness and eligible-row completion against 30; 100% row completion alone does not establish class/group readiness or mean that `reviewed_labels.csv` has been published. The validator exits 1 when not ready; the progress command exits 0 when it successfully prints a report.

The [candidate acquisition workflow](REVIEW_ACQUISITION.md) does not train or approve
labels. Source-reference syntax checks now exclude obvious placeholders from ML
eligibility as well as review publication. Passing these checks is not source
verification. Geographic/time cohort suggestions never enter `FEATURES` and never
automatically populate approved split groups. The 30-row / five-class / ten-group
gate is unchanged.
