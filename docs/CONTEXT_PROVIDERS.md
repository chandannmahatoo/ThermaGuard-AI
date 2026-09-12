# Event context integrations

Weather, air quality, reverse geocoding, EONET, routing and Firebase were previously absent from application code; the template contained future placeholders. The existing backend uses `config.py`, `providers.py`, `main.py` and `database.py`; separate models, schemas and services modules were not present or added.

The four keyless context providers are now enabled in the local environment. Routing and push default to disabled. Their implementation does not change Model V1 features, RandomForest classification, deterministic risk, reviewed labels or model artifacts. Provider context is supporting evidence, not incident confirmation.

## Data contracts and provenance

- Weather uses the configured Open-Meteo forecast endpoint with the real event coordinates and UTC hour of `last_seen_time`. Hourly temperature, humidity, precipitation, wind speed and direction have checked units and numeric bounds. Unsupported historical hours fail explicitly; current weather is never substituted. These are modelled grid values, not on-site measurements.
- Air quality uses the same event hour and coordinates and reports PM2.5, PM10, CO, NO₂ and ozone in μg/m³. Attribution: Open-Meteo / Copernicus CAMS. Missing or malformed arrays and unexpected units are rejected.
- Nominatim reverse lookup normalizes location names. Forward and reverse requests share a one-request-per-1.1-second gate, with identifying User-Agent and cached results. Operate one worker for the public Nominatim service.
- EONET requests open and closed hazards in a ±3-day window. It matches Point geometries within 50 km and 72 hours, reporting the nearest match. Other geometry types are not approximated. No match does not establish that no hazard exists.
- OpenRouteService computes a driving-car route from an authorized event to an explicitly supplied response point. Coordinates are longitude/latitude. Road distance and duration do not guarantee emergency accessibility. Keys are sent in an Authorization header, not query strings. The configured URL is replaceable; deployments should check current provider endpoint availability.

Reference contracts: [Open-Meteo weather](https://open-meteo.com/en/docs), [air quality](https://open-meteo.com/en/docs/air-quality-api), [Nominatim usage](https://operations.osmfoundation.org/policies/nominatim/), [EONET v3](https://eonet.gsfc.nasa.gov/docs/v3), [routing](https://openrouteservice.org/dev/), [Firebase Admin](https://firebase.google.com/docs/admin/setup).

## Caching and transaction boundaries

Successful normalized packets include provider, status, version, fetched time and an event/endpoint signature. Weather/AQ/EONET TTL is one hour, location 30 days, and routing one day. A bounded 512-entry process cache supplements context persisted in event JSON. Signatures include coordinates and, for time-sensitive providers, event time. Routing additionally includes destination. Failed refreshes preserve same-signature prior evidence with explicit refresh status. No fabricated replacement values are emitted.

Sync honors each configured per-provider event limit (0–20), prioritizing missing context, newest timestamps and risk. Additional context has a 60-second overall budget; remaining work is deferred to subsequent syncs. Demo and disabled providers make no requests. Providers run after classification/risk computation and before the brief persistence transaction, using detached event dictionaries. No SQLite write transaction spans provider requests. Existing FIRMS observation commits, WAL, busy timeout and one-worker guidance are retained.

## Routing and notifications

`POST /api/v1/events/{event_id}/route` takes `latitude` and `longitude` for a known destination. It requires authentication and event-area authorization, calls the provider without an open transaction, then stores context only if the event snapshot is unchanged. Disabled routing, missing keys and missing destinations are explicit unavailable states.

FCM is an optional additional channel. Configure an ignored service-account JSON path and a matching project ID, then enable push. Certificate parsing and Firebase initialization are checked; absent/invalid configuration does not break ingestion. The Admin SDK is pinned in backend requirements.

Users must first enable the existing nearby-notification preferences, then register their own existing FCM device token through authenticated `PUT /api/v1/auth/push-device` (`{"token":"..."}`). `DELETE` unregisters that user's device. One token per user is supported. Token ownership conflicts are rejected and tokens are never echoed. Obtaining a device token requires a Firebase-enabled client; this change does not add browser permission prompts or a web service worker.

After the deterministic threshold decision and event/alert commit, eligible opted-in nearby users are checked against event authorization. Email and push are independent. Push reuses the notification ledger with `channel=push`: an event/user/risk claim is committed before sending, including reclustering overlap protection. Failed or interrupted attempts are not automatically retried (at-most-once attempt semantics). Push failure cannot roll back the committed event or alert. Notifications contain a minimal event ID and direct users to the authenticated dashboard. No live push was sent during verification.

`GET /api/v1/admin/diagnostics/context` returns safe configuration states only, explicitly not live health claims. Existing Gemini evidence packets include allowlisted available context and explicit “not available” values otherwise. Selected-event requests include only the selected event; overview retains its existing bounded authorized event set.

The event drawer displays context states, units, timestamps and attribution. Locations appear in map tooltips and event text filtering. Optional destination inputs request a route and its geometry is drawn on the existing map. The existing OSM and satellite displays remain.

## Local verification

Automated tests mock providers and use isolated databases. Local environment provider settings cannot enable network calls in tests. The pre-existing FIRMS route test now explicitly pins its intended single-source fixture; separate multi-source tests retain multi-source coverage.

Read-only live verification used event `TG-firms-b8a3a2f0a7609833415e` at 34.156925, 74.19067, observed 2026-09-11 08:09 UTC. No production records were written by the verification:

| Provider | Result |
| --- | --- |
| Weather | Available at 08:00 UTC: 27.7°C, RH 40%, precipitation 0.3 mm, wind 6.7 km/h from 82° |
| Air quality | Available at 08:00 UTC: PM2.5 22.6, PM10 33.2, CO 182, NO₂ 0.6, ozone 162 μg/m³ |
| Nominatim | Limber, Boniyar, Baramulla, Jammu and Kashmir, India |
| EONET | Successful response; no Point hazard matched within 50 km / 72 h |
| Routing | Disabled; no live route request |
| Firebase | Disabled; no explicit test device, no push sent |

Previously exposed credentials must be rotated before deployment. Keep the local environment and Firebase certificate untracked; the example contains no credentials. The local backend was restarted after verification to load the changed configuration/code. Schema creation adds an empty push-subscription table on startup; provider data appears after a normal authorized enrichment sync, not from synthetic seeding.

Final regression: 317 backend tests passed; 18 frontend tests passed; TypeScript, production build, compileall and dependency consistency checks passed. Only upstream deprecation warnings remain.

Files changed for this implementation: `.gitignore`; `backend/.env` (ignored); `backend/.env.example`; `backend/app/config.py`, `providers.py`, `main.py`, `database.py`; `backend/requirements.txt`; `backend/tests/conftest.py`, `test_context_providers.py`, `test_system.py`; `frontend/app/page.tsx`; `frontend/lib/api.ts`; `frontend/components/ContextPanel.tsx`, `MapView.tsx`; `frontend/package.json`; `frontend/tests/context.test.mjs`; this report. Other pre-existing workspace changes were preserved.
