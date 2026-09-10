# ThermaGuard AI

Compact Smart India Hackathon 2026 MVP for turning satellite thermal observations into traceable events and explainable decision-support risk. NASA FIRMS provides **near-real-time satellite-derived thermal anomaly observations**, not a continuous camera feed.

## Architecture and workflow

Next.js / React / TypeScript / Tailwind / Leaflet / Recharts → FastAPI → SQLite through SQLAlchemy. FIRMS CSV → validation and retained raw provenance → deterministic spatial-temporal connected components → OSM geometry proximity / optional historical context → shared features → reviewed-data Random Forest (when available) → separate abnormality and risk → scoped dashboard, alerts and Ollama explanations.

Python uses NumPy, scikit-learn, Shapely and PyProj. Pandas/GeoPandas are deliberately omitted because these compact ingestion and geometry operations do not require them. There are no microservices or background infrastructure requirements.

## Setup

Python 3.12+ and Node.js 22+ recommended. Install dependencies outside source control. Development dependency directories are temporary runtime artifacts, not deliverables.

```sh
python3 -m venv /tmp/thermaguard-venv
/tmp/thermaguard-venv/bin/pip install -r backend/requirements.txt
cd backend
cp .env.example .env
/tmp/thermaguard-venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000. The Next.js server proxies API requests to `http://127.0.0.1:8000`; override the server-only `BACKEND_URL` environment variable if needed. No provider secrets enter browser bundles.

All provider HTTP clients identify themselves with a `ThermaGuardAI-Hackathon/0.1` User-Agent header; public APIs (Overpass, Nominatim, FIRMS, Copernicus) reject or throttle unidentified clients.

### Demo access

With `DEMO_MODE=true`, use the login screen's demo account buttons. Password: `DemoTherma2026!`; emails: `admin@demo.thermaguard.local` and `operator@demo.thermaguard.local`. These publicly documented credentials exist **only for local demo mode**. JWT signing uses a random process secret if none is configured in demo; restarting invalidates tokens. Tokens remain in browser memory, so refresh requires login.

One fixture CSV creates 10 detections, four events, one fictional organization, and one threshold alert. Coordinates are illustrative and make no claim about an actual incident or facility. All observations have `is_demo=true`. Demo dates are fixed at 10–11 September 2026, and demo analytics anchor to the latest fixture time. No classes, model probabilities, industrial facilities or satellite context are fabricated.

### Real mode

Use a separate database, set `DEMO_MODE=false`, supply a strong `JWT_SECRET` and `FIRMS_MAP_KEY`, and create an administrator interactively:

```sh
cd backend
/tmp/thermaguard-venv/bin/python -m app.bootstrap
```

Use System status → Synchronize FIRMS, or `POST /api/v1/firms/sync` with `{ "bounds": [68,6,98,38], "days": 1 }`. Real synchronization is rejected in demo mode. Existing observations are deduplicated by source identity. Failed providers leave stored events available. Public registration creates an unassigned organization user; an administrator must create an organization, assign an area, and connect the user.

## Configuration

See `backend/.env.example`. Important controls: SQLite `DATABASE_URL`; JWT secret, algorithm and expiry; FIRMS key and endpoint; Overpass endpoint; Copernicus satellite credentials (client ID/secret, token URL, base URL); cluster radius/time; alert threshold and JSON `RISK_WEIGHTS`; CORS origins; Ollama URL/model/enabled; SMTP host/port/user/password/from. SMTP uses STARTTLS and never sends fixture alerts. Ollama is optional and only explains bounded authorized records. `RISK_WEIGHTS` is validated at startup: all seven keys required, no negative values, total exactly 100 — the server refuses to start on invalid configuration. Failed logins are throttled (10 failures per email per 5 minutes, successful logins are not counted).

## APIs

Interactive contracts: http://localhost:8000/docs. `/health` is public; all event, analytics, model, alert and copilot routes require JWT. Administrator-only operations include FIRMS sync, training, organizations, assignments and user organization linking. Event evidence/history/risk share backend area authorization; organization alerts are filtered by organization ID.

Main routes: `/api/v1/auth/{register,login,me}`, `/firms/{sync,status}`, `/events`, `/events/{id}/{evidence,history,risk}`, `/analytics/{summary,trends}` (24h/7d/30d/365d), `/model/{status,train,metrics}`, `/alerts`, `/alerts/{id}/acknowledge`, `/admin/{organizations,assignments}`, `/admin/users/assign`, `/admin/threshold`, `/areas/search`, `/copilot/chat`. State/city lookup uses OpenStreetMap Nominatim bounding boxes, with a per-process request limit and cache. It does not alter authorization.

Analytics windows are 24 hours, 7 days, 30 days or 365 days. When the active dataset has no records inside the requested window, the API returns `available=false, reason=insufficient_history` and the dashboard shows "Insufficient historical data" instead of an empty chart. The demo fixture anchors to its fixed dates, so yearly windows on demo data reflect only the fixture days.

### Satellite context (Copernicus)

In real mode, each non-demo event requests mean NDVI from the Copernicus Data Space Statistical API (Sentinel-2 L2A, ~2 km around the event center, least-cloudy compositing, statistics only — no scene download, no raster stack). OAuth2 client-credential tokens are fetched once and reused until shortly before expiry. Context reports `satellite_context_available` with `ndvi` and `acquisition_date` on success, or an explicit reason (`credentials_missing`, `provider_unavailable`, `demo_mode`) without inventing values. Set `COPERNICUS_CLIENT_ID` and `COPERNICUS_CLIENT_SECRET` to enable; without them satellite context is explicitly `credentials_missing`.

## Model readiness

No reviewed labels or trained model are included. `/api/v1/model/status` exposes the blocker; classes and confidence remain null. Copy the header-only `data/templates/reviewed_labels.csv` to `data/reviewed_labels.csv` and supply reviewed, non-demo, event-level feature records with source references, reviewer and independent geographic/temporal split groups. At least 30 eligible rows, all five classes and 10 independent groups are required. Training further requires all classes in train, validation and test groups; small datasets may not pass this gate. Metrics are computed from actual held-out records only. See [model details](docs/MODEL.md).

## Verification

```sh
cd backend
PYTHONDONTWRITEBYTECODE=1 /tmp/thermaguard-venv/bin/python -m pytest -p no:cacheprovider tests -q
cd ../frontend
npm run typecheck
npm run build
```

Tests use isolated SQLite and mocked provider HTTP responses. They do not establish live provider availability or scientific model quality. Browser QA covers demo login, event evidence and organization restrictions when a browser is available.

## Known limitations and production roadmap

This is a local hackathon MVP, not an emergency dispatch system. OSM completeness varies; query distances are limited to 5 km. Unsupported relation geometries are skipped. Clustering is deterministic single-linkage (chains can span longer than a pairwise radius/time threshold), O(n²), and rebuilds the active dataset on sync. Use bounded regional ingestion: more than 500 observations in one fetch is rejected; at most five previously unenriched events query OSM per sync. Further events explicitly report deferred context and are retried on subsequent syncs. Cached OSM context currently has no automatic expiry. Baseline comparison uses earlier nearby event FRP, brightness, detection frequency, spread and duration. These are heuristic ratios; satellite raster extraction remains blocked. Risk weights are engineering heuristics, not validated safety estimates. UI sections share a compact single workspace route. Live data, SMTP delivery and Ollama require separately configured services. Multi-process model activation, migration tooling, distributed jobs, MFA, login throttling, password recovery, durable delivery retries, audit trails and retention policies are not implemented.

Before production: validate labels and thresholds with domain experts; add spatial/time indexing and migrations; use PostgreSQL/PostGIS with an installed driver; implement complete relation geometry, provider caching and retrieval scheduling; version reviewed datasets and model activation atomically; harden authentication and notification retries. Do not expose the demo server publicly.

## Verified delivery status

Backend: 23 automated tests passed, zero failed. Frontend: TypeScript check and production build passed. Tests emit two upstream Starlette deprecation warnings.

FIRMS is in DEMO mode: real ingestion is implemented and mocked integration tested, but no MAP key is configured, so no live FIRMS request was made. OSM Overpass context is verified REAL live: one small real 5 km query returned distances, counts and attribution through the existing adapter (a missing User-Agent header previously caused HTTP 406 rejections and has been fixed). Satellite context is implemented against the Copernicus Data Space Statistical API (NDVI statistics only) but remains BLOCKED locally pending credentials; success, `credentials_missing` and `provider_unavailable` paths are mock-tested, and demo events are explicitly blocked from live satellite calls. Model training is BLOCKED: no legitimate reviewed dataset was supplied (0 eligible labels). Ollama uses the verified FALLBACK; no running model service was detected on localhost. SMTP delivery is implemented but unconfigured locally, so alerts record `email_unconfigured` and use the dashboard fallback. This is a verified local demo, not production-ready emergency software.
