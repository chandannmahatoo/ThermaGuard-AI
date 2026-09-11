# Architecture

Detect → validate → cluster → enrich → build shared features → classify only with a trained artifact → compare historical behavior → score risk → authorize → present/notify.

`backend/app/main.py` owns HTTP orchestration, provider status and transactional event processing. `database.py` stores users, organizations, bounds assignments, provenance-bearing detections and events, and organization alerts. Event context, features, classification and risk are embedded JSON, avoiding duplicate tables. `providers.py` contains the one FIRMS client, one OSM client and one Copernicus satellite context client. `intelligence.py` owns clustering, features and risk. `ml.py` owns reviewed-data readiness, grouped training and prediction. `security.py` owns scrypt password hashing, JWT (algorithm owned by config), failed-login throttling and geographic access. `bootstrap.py` creates a real administrator without a source-controlled password.

The frontend uses a single compact workspace with six views, a client-only Leaflet map, event detail drawer and copilot panel. Calls pass through the Next.js server proxy. Server roles and bounds, not UI visibility, enforce data access.

External HTTP requests have explicit timeouts and identify the project with a User-Agent header (public Overpass/Nominatim endpoints reject unidentified clients with 406). FIRMS failure returns 503 while existing data remains available. OSM failure records unavailable context. Satellite context calls the Copernicus Data Space Statistical API for NDVI statistics around an event (~2 km, no scene download) with reused OAuth2 tokens; missing credentials, provider failure and demo mode each produce an explicit unavailability reason, never fabricated values. Ollama errors return deterministic evidence summaries. SMTP failures persist on the alert; fixtures never send email.

Analytics windows accept 24h/7d/30d/365d and return `available=false, reason=insufficient_history` when the visible dataset holds no records in the window; the dashboard renders an explicit notice instead of an empty chart.

The backend is designed for a single local process. SQLite and JSON keep setup small; production geospatial indexing and transactional model versioning are future work. The supplied workflow image is preserved at `docs/workflow.png`.
