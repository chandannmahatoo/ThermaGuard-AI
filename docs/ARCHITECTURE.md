# Architecture

Detect → validate → cluster → enrich → build shared features → classify only with a trained artifact → compare historical behavior → score risk → authorize → present/notify.

`backend/app/main.py` owns HTTP orchestration, provider status and transactional event processing. `database.py` stores users, organizations, bounds assignments, provenance-bearing detections and events, and organization alerts. Event context, features, classification and risk are embedded JSON, avoiding duplicate tables. `providers.py` contains the one FIRMS client, one OSM client and one Copernicus satellite context client. `intelligence.py` owns clustering, features and risk. `ml.py` owns reviewed-data readiness, grouped training and prediction. `security.py` owns scrypt password hashing, JWT (algorithm owned by config), failed-login throttling and geographic access. `bootstrap.py` creates a real administrator without a source-controlled password.

The frontend uses a single compact workspace with six views, a client-only Leaflet map, event detail drawer and copilot panel. The browser API client uses configured absolute API and health URLs; optional Next.js rewrites remain available for same-origin callers. Server roles and bounds, not UI visibility, enforce data access.

External HTTP requests have explicit timeouts and identify the project with a User-Agent header (public Overpass/Nominatim endpoints reject unidentified clients with 406). FIRMS failure returns 503 while existing data remains available. OSM failure records unavailable context. Satellite context calls the Copernicus Data Space Statistical API for NDVI statistics around an event (~2 km, no scene download) with reused OAuth2 tokens; missing credentials, provider failure and demo mode each produce an explicit unavailability reason, never fabricated values. Gemini errors return deterministic evidence summaries. SMTP failures persist on the alert; fixtures never send email.

Analytics windows accept 24h/7d/30d/365d and return `available=false, reason=insufficient_history` when the visible dataset holds no records in the window; the dashboard renders an explicit notice instead of an empty chart.

The backend is designed for a single local process. SQLite and JSON keep setup small; production geospatial indexing and transactional model versioning are future work. The supplied workflow image is preserved at `docs/workflow.png`.

Clustering groups nearby detections in space and time; it does not classify them. The Random Forest classifies, the deterministic risk engine scores, and Gemini explains authorized evidence without writing events or labels.

## Data policy and sources

NASA FIRMS observations follow the official [area CSV API](https://firms.modaps.eosdis.nasa.gov/api/area/). Latitude/longitude, date/time, FRP and brightness are validated; confidence stays in original sensor-specific form instead of being falsely equated to model confidence. Raw rows, source identity, retrieval time, observed time, provider, processing version and demo flag are retained. Deduplication hashes observation identity, not mutable retrieval times.

OpenStreetMap context uses [Overpass QL](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL), requesting nodes and way geometries within 5 km. Requests identify the project with a User-Agent header; unauthenticated client libraries sending no User-Agent are rejected with HTTP 406. Distances are computed in a local azimuthal equidistant projection to geometry boundaries/interiors, not arbitrary polygon centers. Supported context includes industrial land, refineries, factories, power plants, forest, farmland and residential areas, plus facility counts and the land-use class at the event location. No match means unknown beyond the query area; absence of tagging is not proof of absence. Complex relations without directly usable geometry are skipped. OSM data attribution is required; the map uses and credits OpenStreetMap standard tiles. State/city lookup uses Nominatim returned bounding boxes, not invented administrative polygons; boxes are approximate filters.

Satellite context is fetched per event from the Copernicus Data Space Statistical API (Sentinel Hub compatible) using OAuth2 client credentials: a ~2 km bounding box around the event, Sentinel-2 L2A, least-cloudy mosaicking, daily aggregation over a window from seven days before to seven days after the event, capped at the current time, and an evalscript computing NDVI server-side. Only compact statistics (mean NDVI, sample counts, interval date) are read back; no scenes, rasters or heavy processing stacks are used. Values are reported only when real pixels were observed; otherwise the context states `credentials_missing`, `provider_unavailable` or `demo_mode` and NDVI stays null. Provider, source, retrieval time and image reference are stored alongside the value for provenance.

Satellite land-cover and built-up fractions remain null; only measured NDVI statistics from the Copernicus adapter are ever reported, and only for real (non-demo) events in real mode. Do not replace these with invented values.

`data/demo/detections.csv` is the only deterministic demo fixture. Its coordinates/thermal values illustrate application behavior and are not real-world observations. They carry `is_demo=true` at ingestion. Live and demo data are filtered independently throughout clustering, APIs and alerts. Real synchronization is blocked in demo mode. Training requires explicitly non-demo reviewed records.

`data/templates/reviewed_labels.csv` contains only an input header. A human reviewer is responsible for labels and source traceability. Do not copy demo values into it as real records.

Review workflow: `backend/export_review_candidates.py` exports all real non-demo events to `data/review_candidates.csv` with reviewer-assistance context (coordinates, timestamps, land use, abnormality, risk, facility names). Re-exports preserve existing manual review fields for matching events, append new events deterministically and report removed/reclustered events instead of discarding them silently. Assistance columns are ignored by the training pipeline (`ml.py` reads exactly `REVIEW_META + FEATURES`). Humans fill `label`, `split_group`, `reviewer` and `source_reference` and set `reviewed=true`; the canonical workflow never infers labels. `backend/validate_review_candidates.py` reports duplicates, invalid labels, demo contamination, incomplete reviewed rows and the exact training-gate shortfall. `backend/finalize_reviewed_labels.py` publishes only complete reviewed rows to `data/reviewed_labels.csv` and refuses to write anything when a reviewed row is invalid.

Reviewer safety additions: `review_event_summary.py` prints only stored non-demo event evidence and an unchecked neutral checklist. `prepare_review_row.py` is read-only unless explicit metadata flags are supplied; it never updates ML feature cells. `review_progress.py` uses the unchanged `ml.dataset` eligibility and readiness gate. The exporter and finalizer now preserve replaced CSVs in timestamped `data/backups/` files, reject duplicate IDs, and avoid silently losing custom reviewer notes or removed/reclustered rows. See the exact contract and commands in [MODEL.md](MODEL.md#human-review-csv-contract-audited-against-feature-version-2). These canonical tools do not generate labels or approvals. The optional assisted_review.py helper proposes heuristics for human confirmation; its suggestions are not independent evidence.

Real acquisition plans and packet generation: see [REVIEW_ACQUISITION.md](REVIEW_ACQUISITION.md).
Search zones and suggested cohort names are reviewer assistance only. New stored
FIRMS detections retain their raw observations and acquisition query metadata.
Approved evidence changes stop acquisition for human reconciliation.

## Multi-source FIRMS ingestion

The canonical supported hotspot schema catalog is `config.FIRMS_SOURCES`. The
provider intersects it with NASA's authenticated [data availability API](https://firms.modaps.eosdis.nasa.gov/api/data_availability/)
and uses the returned min/max dates, cached for five minutes with a single-flight
lock. Availability failures stop ingestion safely; unsupported or out-of-range
selections return 422. Date limits are never compiled into the application.
Burned-area products (BA_MODIS/BA_VIIRS), GOES and Landsat are not included in this
hotspot schema adapter, even when the catalog lists them.

`GET /api/v1/firms/sources` returns authenticated, credential-free source metadata.
`POST /api/v1/firms/sync` accepts optional `sources`, selecting distinct NRT sources.
The default remains S-NPP for compatibility; `FIRMS_LIVE_SOURCES` can select, for
example, S-NPP and NOAA-20. Sequential requests bound concurrency to one. The
combined accepted-observation budget is checked before any source is persisted;
if a source fails, the live batch is not partially inserted. A metadata refresh
adds at most one request to the configured area-request budget.

The existing historical backfill route accepts any supported, currently available
source, with SP preferred for historical acquisition. It validates the entire
requested interval before downloading, chunks into at most five days, and caps
area requests with `FIRMS_MAX_REQUESTS` (default/max 12; up to 60 days per call).
Earlier successful chunks remain committed if a later chunk fails; replay is
idempotent. Historical processing retains its no-notification/no-live-enrichment
policy. The existing acquisition CLI remains the reviewed-evidence-preserving
path; later explicit enrichment and human review precede training publication.

Detections retain the original raw row plus dataset, instrument, satellite,
version, observed/acquired time, scan, track, primary/secondary measurements and
sensor-band names. VIIRS uses bright_ti4/bright_ti5; MODIS uses
brightness/bright_t31. Missing optional measurements remain null. Neither schema
is filled with the other's band values. Generic `brightness` and legacy event
brightness summaries remain descriptive compatibility fields, not harmonized
measurements; comparisons across sensors require scientific caution.

Identity includes dataset, satellite, instrument, normalized coordinates and UTC
observation time. Retrieval time and revised version values do not create a new
observation. Separate sensors and NRT/SP processing families remain separate
observations; they can share one spatial-temporal event. NRT/SP can describe the
same physical overpass, so counts are not independent confirmations.

Legacy records with documented acquisition_query.source can match the new
identity without changing their stored IDs or payloads. If an incoming observation
matches a legacy record whose dataset is unknown, ingestion refuses it for human
provenance reconciliation rather than guessing a source or creating a second row.
No migration or relabeling occurs automatically. New clustering retains source
counts, per-band sensor summaries and grouped sensor/version/time provenance.

`GET /api/v1/firms/detections?offset=0&limit=100` provides paginated raw observations
(maximum page size 500) only from events visible to the caller, matching the
existing event-evidence authorization boundary. The event map remains unchanged;
the event drawer shows source counts and already exposes raw evidence. No second
map mode or additional primary-map markers were introduced.
