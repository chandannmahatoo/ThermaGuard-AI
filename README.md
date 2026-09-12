# ThermaGuard AI

Compact Smart India Hackathon 2026 MVP for turning satellite thermal observations into traceable events and explainable decision-support risk. NASA FIRMS provides **near-real-time satellite-derived thermal anomaly observations**, not a continuous camera feed.

## Architecture and workflow

Next.js / React / TypeScript / Tailwind / Leaflet / Recharts → FastAPI → SQLite through SQLAlchemy. FIRMS CSV → validation and retained raw provenance → deterministic spatial-temporal connected components → OSM geometry proximity / optional historical context → shared features → reviewed-data Random Forest (when available) → separate abnormality and risk → scoped dashboard, alerts and Gemini explanations.

Python uses NumPy, scikit-learn, Shapely and PyProj. The application pipeline needs neither Pandas nor GeoPandas. Two retained optional review helpers use Pandas and are outside the supported dependency set; prefer the standard-library review commands below. There are no microservices or background infrastructure requirements.

## Setup

Python 3.12+ and Node.js 22+ recommended. Install dependencies outside source control. Development dependency directories are temporary runtime artifacts, not deliverables.

Run all backend commands from the repository root so the relative SQLite URL always selects the same database.

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env  # first setup only; preserve existing credentials
cp frontend/.env.example frontend/.env.local
npm --prefix frontend ci
PYTHONPATH=backend ./.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, from the repository root:

```sh
npm --prefix frontend run dev
```

Open [ThermaGuard](http://127.0.0.1:3000). The browser calls same-origin `/api/v1` and `/health` routes, which Next.js proxies using server-only `BACKEND_URL` (default `http://127.0.0.1:8000`). Optional `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_BACKEND_URL` override browser destinations for a separate API deployment. Restart development or rebuild after configuration changes. Provider secrets belong only in ignored `backend/.env`.

All provider HTTP clients identify themselves with a `ThermaGuardAI-Hackathon/0.1` User-Agent header; public APIs (Overpass, Nominatim, FIRMS, Copernicus) reject or throttle unidentified clients.

### Demo access

With `DEMO_MODE=true`, use the login screen's demo account buttons. Password: `DemoTherma2026!`; emails: `admin@demo.thermaguard.local` and `operator@demo.thermaguard.local`. These publicly documented credentials exist **only for local demo mode**. JWT signing uses a random process secret if none is configured in demo; restarting invalidates tokens. Tokens remain in browser memory, so refresh requires login.

One fixture CSV creates 10 detections, four events, one fictional organization, and one threshold alert. Coordinates are illustrative and make no claim about an actual incident or facility. All observations have `is_demo=true`. Demo dates are fixed at 10–11 September 2026, and demo analytics anchor to the latest fixture time. No classes, model probabilities, industrial facilities or satellite context are fabricated.

### Real mode

Use a separate database, set `DEMO_MODE=false`, supply a strong `JWT_SECRET` and `FIRMS_MAP_KEY`, and create an administrator interactively:

```sh
PYTHONPATH=backend ./.venv/bin/python -m app.bootstrap
```

Use System status → Synchronize FIRMS, or `POST /api/v1/firms/sync` with `{ "bounds": [68,6,98,38], "days": 1 }`. Real synchronization is rejected in demo mode. Existing observations are deduplicated by source identity. Failed providers leave stored events available. Public registration creates an unassigned organization user; an administrator must create an organization, assign an area, and connect the user.

## Configuration

See `backend/.env.example`. Important controls: SQLite `DATABASE_URL`; JWT secret, algorithm and expiry; FIRMS key and endpoint; Overpass endpoint; Copernicus satellite credentials (client ID/secret, token URL, base URL); cluster radius/time; alert threshold and JSON `RISK_WEIGHTS`; CORS origins; Gemini API key/model/enabled; SMTP host/port/user/password/from. SMTP uses STARTTLS and never sends fixture alerts. Gemini is optional and only explains bounded authorized records. `RISK_WEIGHTS` is validated at startup: all seven keys required, no negative values, total exactly 100 — the server refuses to start on invalid configuration. Failed logins are throttled (10 failures per email per 5 minutes, successful logins are not counted).

### External context providers

Optional providers enrich events with verified, cached context: **Weather** and **Air quality** (Open-Meteo/CAMS, modelled grid for the event hour), **Geocoding** (Nominatim reverse, 1 req/s gate), **NASA EONET** (50 km/72 h hazard match per event, plus a current open-hazards map layer), **Routing** (OpenRouteService driving routes to a chosen response point; requires `OPENROUTESERVICE_API_KEY`), and **Firebase push** (requires `FIREBASE_PROJECT_ID` plus a service-account JSON; alerts are only pushed to explicitly registered devices). Each is gated by its `*_ENABLED` flag, budgeted per sync (`*_EVENTS_PER_SYNC`), and failure-isolated: a provider outage never blocks ingestion, classification, risk or alerts. Missing context is reported as unavailable with a reason — never inferred. `GET /api/v1/providers/status` reports each provider's configuration state plus the last real interaction (success/failure category, latency) recorded in the running process; no credentials are ever included.

## APIs

Interactive contracts: http://localhost:8000/docs. `/health` is public; all event, analytics, model, alert and copilot routes require JWT. Administrator-only operations include FIRMS sync, training, organizations, assignments and user organization linking. Event evidence/history/risk share backend area authorization; organization alerts are filtered by organization ID.

Main routes: `/api/v1/auth/{register,login,me,notifications,push-device}`, `/firms/{sync,status}`, `/events`, `/events/{id}/{evidence,history,risk,route}`, `/analytics/{summary,trends}` (24h/7d/30d/365d), `/model/{status,train,metrics}`, `/alerts`, `/alerts/{id}/acknowledge`, `/providers/status`, `/eonet/events`, `/admin/{organizations,assignments}`, `/admin/users/assign`, `/admin/threshold`, `/areas/search`, `/copilot/chat`. State/city lookup uses OpenStreetMap Nominatim bounding boxes, with a per-process request limit and cache. It does not alter authorization.

Analytics windows are 24 hours, 7 days, 30 days or 365 days. When the active dataset has no records inside the requested window, the API returns `available=false, reason=insufficient_history` and the dashboard shows "Insufficient historical data" instead of an empty chart. The demo fixture anchors to its fixed dates, so yearly windows on demo data reflect only the fixture days.

### Satellite context (Copernicus)

In real mode, each non-demo event requests mean NDVI from the Copernicus Data Space Statistical API (Sentinel-2 L2A, ~2 km around the event center, least-cloudy compositing, statistics only — no scene download, no raster stack). OAuth2 client-credential tokens are fetched once and reused until shortly before expiry. Context reports `satellite_context_available` with `ndvi` and `acquisition_date` on success, or an explicit reason (`credentials_missing`, `provider_unavailable`, `demo_mode`) without inventing values. Set `COPERNICUS_CLIENT_ID` and `COPERNICUS_CLIENT_SECRET` to enable; without them satellite context is explicitly `credentials_missing`.

## Model readiness

The current local workspace contains 33 eligible published review rows and an existing model artifact. Model files are git-ignored and may be absent in a fresh clone; `/api/v1/model/status` reports availability, with null classes/confidence when unavailable. Cleanup does not train or alter model bytes. To build a legitimate reviewed dataset from real ingested events: run `PYTHONPATH=backend ./.venv/bin/python backend/export_review_candidates.py` to produce `data/review_candidates.csv` (manual review fields are preserved on re-export; demo events are excluded), let human reviewers fill `label`, `split_group`, `reviewer` and `source_reference` and set `reviewed=true` — the canonical workflow does not infer labels — then check readiness with `backend/validate_review_candidates.py` and publish with `backend/finalize_reviewed_labels.py`, which writes only complete reviewed rows to `data/reviewed_labels.csv` and refuses incomplete ones. At least 30 eligible rows, all five classes and 10 independent groups are required. Training further requires all classes in train, validation and test groups; small datasets may not pass this gate. Metrics are computed from actual held-out records only. `GET /api/v1/model/review-readiness` exposes the same readiness gate; `GET /api/v1/model/review-candidates` is a read-only admin export. See [model details](docs/MODEL.md).

## Human review helpers

Use `backend/review_event_summary.py EVENT_ID` for a neutral stored-evidence summary and checklist, or `backend/prepare_review_row.py EVENT_ID` to also inspect existing review fields. Both are read-only by default. Run them with `PYTHONPATH=backend ./.venv/bin/python` from the project root. Explicit metadata-update flags are validated and create timestamped CSV backups; no code assigns a label or approves its own evidence. `backend/review_progress.py` reports candidate counts, class/group coverage and the unchanged training gate. See [the exact CSV contract and commands](docs/MODEL.md#human-review-csv-contract-audited-against-feature-version-2) before approving rows. Do not run training while readiness is NO.

## Verification

```sh
./.venv/bin/python -m pip check
./.venv/bin/python -m py_compile backend/app/*.py
PYTHONPATH=backend ./.venv/bin/pytest backend/tests -q
node --test frontend/tests/api.test.mjs
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Tests use isolated SQLite and mocked provider HTTP responses. They do not establish live provider availability or scientific model quality. Browser QA covers demo login, event evidence and organization restrictions when a browser is available.

## Known limitations and production roadmap

This is a local hackathon MVP, not an emergency dispatch system. OSM completeness varies; query distances are limited to 5 km. Unsupported relation geometries are skipped. Clustering is deterministic single-linkage (chains can span longer than a pairwise radius/time threshold), O(n²), and rebuilds the active dataset on sync. Use bounded regional ingestion: more than 500 observations in one fetch is rejected; at most five previously unenriched events query OSM per sync. Further events explicitly report deferred context and are retried on subsequent syncs. Cached OSM context currently has no automatic expiry. Baseline comparison uses earlier nearby event FRP, brightness, detection frequency, spread and duration. These are heuristic ratios; satellite enrichment reads measured NDVI statistics without downloading rasters. Risk weights are engineering heuristics, not validated safety estimates. UI sections share a compact single workspace route. Live data, SMTP delivery and Gemini require separately configured services. Multi-process model activation, migration tooling, distributed jobs, MFA, password recovery, durable delivery retries, audit trails and retention policies are not implemented.

Before production: validate labels and thresholds with domain experts; add spatial/time indexing and migrations; use PostgreSQL/PostGIS with an installed driver; implement complete relation geometry, provider caching and retrieval scheduling; version reviewed datasets and model activation atomically; harden authentication and notification retries. Do not expose the demo server publicly.

## Verification status and operating limits

See [cleanup audit](docs/CLEANUP_MANIFEST.md) for the current verification results and integrity checks, and [runtime reliability](docs/RUNTIME_RELIABILITY.md) for the earlier measured live-provider run. Live service availability depends on the current local credentials and configured Gemini model; earlier measurements are not a guarantee of present availability.

Clustering groups nearby observations in space and time; it does not classify events. Random Forest with SimpleImputer performs classification from reviewed-only data with group-aware splits. Risk is a separate deterministic score, not ML confidence. Gemini only explains authorized event evidence; it has no route to modify classification, risk or labels. Set `GEMINI_ENABLED=true`, `GEMINI_API_KEY`, and `GEMINI_MODEL=gemini-2.5-flash` for the intended setup. Provider/model errors fall back to an explicitly identified deterministic summary.

SQLite uses WAL, foreign keys and a busy timeout. Ingestion releases unnecessary transactions before provider requests, rejects overlapping in-process ingestion with 409, rolls back contention with controlled 503 responses, reuses valid satellite context and sends SMTP after commit. Run one backend process and avoid concurrent acquisition CLI writes. Deferred satellite enrichment can lag behind repeatedly unavailable earlier events; pending email is not a durable retry queue.

Real candidate expansion, evidence packets, read-only inventory/queue, and safe
cohort naming are documented in [docs/REVIEW_ACQUISITION.md](docs/REVIEW_ACQUISITION.md).
Acquisition preserves approved evidence, suppresses historical alerts, and never trains.

Source provenance, geometry limitations and demo separation are documented in [architecture and data policy](docs/ARCHITECTURE.md). The `assisted_review.py` suggestions are heuristic assistance requiring personal verification; a generic source URL or a syntactically valid CSV does not establish label authenticity or group independence.

## Selecting FIRMS sources

Use authenticated `GET /api/v1/firms/sources` to discover supported datasets and
current date ranges. Live sync remains compatible with the existing body, and can
also select sources explicitly:

```json
{"sources":["VIIRS_SNPP_NRT","VIIRS_NOAA20_NRT"],"bounds":[72.5,21.0,72.8,21.2],"days":1}
```

NRT supports current monitoring. Prefer available SP datasets for historical
collection through `/api/v1/firms/history/backfill`; choose dates from availability
metadata. Supported hotspot schemas include S-NPP, NOAA-20, NOAA-21 NRT and MODIS,
plus S-NPP, NOAA-20 and MODIS SP. See [source/provenance policy](docs/ARCHITECTURE.md#multi-source-firms-ingestion)
and [sensor/model limits](docs/MODEL.md#multi-sensor-evidence-and-the-existing-trained-model).
Raw FIRMS detections are observations; ThermaGuard events are clusters;
human-reviewed events are training units. Multi-source collection does not train
the model or create labels. The installed model's MODIS/mixed-sensor predictions
remain unavailable pending an explicitly approved model revision.

### Actual multi-source candidates and Model V2 audit

The local collection on 11 September 2026 contains **651 real observations from all seven FIRMS sources**, clustered into **297 events**. There are **264 new unreviewed candidates**; no human labels or model artifacts were generated. Model V2 is **not ready**. The original 33 reviews need timestamped re-review and existing evidence/split issues must be resolved. Full source counts, acquisition windows, matrices and limitations: [acquisition audit](docs/REVIEW_ACQUISITION_REPORT.md). Feature proposal: [Model V2](docs/MODEL.md#future-model-v2-evidence-proposal-not-a-trained-model).

Run from the repository root using the project environment:

```bash
PYTHONPATH=backend ./.venv/bin/python backend/review_progress.py --v2
PYTHONPATH=backend ./.venv/bin/python backend/review_progress.py --reconcile-sources
```

The second command is a dry run; `--apply` intentionally writes only unambiguous provenance. CLI acquisition/enrichment must run with the API paused because the ingestion lock is process-local. The existing bounded plan is `data/review_acquisition_plan.json`; its `freeze_reviewed` option preserves prior reviewed event/CSV snapshots and rejects incoming clusters that would alter them. It does not reapprove stale evidence. Re-check current availability before choosing dates. `acquire_review_candidates.py --enrich-unreviewed` uses the existing OSM/Copernicus per-run budgets, with no alerts or training. Evidence packets remain under `data/review_packets/`.

The map selector switches between clustered events and raw FIRMS hotspots. Raw mode paginates the existing authorized detection API and shows sensor/source, UTC acquisition time and FRP in each marker tooltip. One raw marker represents one observation; event markers represent clusters. Neither map view constitutes human review.

After the API was restored, a separate live sync increased the observed database to **790 real detections / 405 events**. The canonical candidate file and packets now contain **372 unreviewed events**. This includes 108 events added after the controlled collection. The audit distinguishes both checkpoints; no extra human labels were assigned.

### Remote Copilot and subscribed email alerts

Copilot uses the internet-hosted Gemini API with a configurable timeout and deterministic fallback. Only the selected event's allowlisted evidence is sent remotely; overview summaries remain deterministic. Configure `GEMINI_ENABLED`, `GEMINI_API_KEY`, `GEMINI_MODEL`, and `GEMINI_TIMEOUT_SECONDS` in the untracked `backend/.env`.

Email alerts use Gmail STARTTLS and a Google App Password. Configure the `SMTP_*` variables in `backend/.env.example`; never use or commit a normal Gmail password. Existing users are opted out by default. Authenticated `GET`/`PUT /api/v1/auth/notifications` manages a user's location, optional radius and opt-in. Only authorized, nearby subscribers receive an event-level email after the database commits; a durable per-user/severity record prevents duplicate attempts. Organization dashboard alerts remain available when email fails.

Admin-only diagnostics: `POST /api/v1/admin/diagnostics/gemini` and `POST /api/v1/admin/diagnostics/smtp`. The latter sends one intentional test message to the configured test recipient/sender. The Gemini diagnostic uses a harmless fixed prompt, reports reachability and timing, and never returns the API key or answer text. Full configuration, migration, delivery guarantees, test results and limitations: [runtime reliability](docs/RUNTIME_RELIABILITY.md).
