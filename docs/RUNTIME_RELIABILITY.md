# FIRMS runtime reliability repair

## Confirmed cause

The previous `process()` inserted and flushed detections before awaiting OSM and
Copernicus, then updated/flushed events repeatedly and committed only at the end.
An SQLite writer could therefore remain reserved throughout slow network calls.
Concurrent synchronization or an unrelated writer could exhaust SQLite's previous
short default wait and raise `OperationalError: database is locked`. Successful
satellite context was fetched repeatedly, and a failed refresh could erase it.
SMTP was also performed before the alert transaction committed.

## Transaction and concurrency changes

1. Normal ingestion stores deduplicated detections in a short initial transaction.
   It then copies detection/event evidence into dictionaries and releases the read
   transaction. If later event persistence fails, valid acquired detections remain
   available for the next full rebuild.
2. Clustering, bounded provider calls, classification and risk run on detached
   dictionaries. No database write transaction is held across these provider awaits.
3. Persistence reserves the SQLite writer with `BEGIN IMMEDIATE` before checking
   the snapshot, batches changed/new event payloads, migrates alert identities, and
   commits. Unchanged events are not assigned new payloads. Flushes occur at batch
   foreign-key boundaries, not once per event. Removed-parent cases need an extra
   flush to move/delete referencing alerts before deleting old event rows.
4. SMTP delivery occurs after the alert/event commit, with a separate short
   transaction for its outcome. No SMTP request runs while holding the event write
   transaction. This MVP queue is not a durable message-delivery worker: a crash
   after commit may leave an `email_pending` status requiring operator attention.

The offline human-review acquisition path remains special: `commit=False` requires
`enrich=False` and notifications disabled. It keeps the batch atomic so reviewed
snapshots can be checked and the entire batch rolled back. It makes no live
provider calls inside `process()`.

Current sync and historical backfill share one application-level `asyncio.Lock`.
An overlapping operation receives **409: FIRMS synchronization already in progress**.
The guard covers FIRMS fetching and the whole ingestion run. Database operational
errors roll back the session and return **503: Database temporarily busy; retry
synchronization.** SQL parameters, event payloads, tokens and provider error bodies
are not logged. Request dependencies also roll back on exceptional exit.

Run SQLite with **one application worker/process**. The guard is process-local;
independent CLI tools, reload processes and multiple worker processes do not share
it. Snapshot checks reject stale computation, but they do not provide distributed
coordination. Do not run acquisition CLIs and live synchronization simultaneously.
SQLite may still return the controlled 503 if another writer holds the database
past the configured timeout. This is resilience, not a claim that contention is
impossible.

## SQLite configuration

Only SQLite engines receive:

- connection `timeout=30`, `check_same_thread=False`;
- `foreign_keys=ON`;
- `journal_mode=WAL`;
- `busy_timeout=30000`.

`FULL` synchronous durability is retained; `NORMAL` is not enabled. The real
configured database was checked: WAL, foreign keys enabled, 30,000 ms busy timeout,
and synchronous value 2. SQLite WAL/SHM sidecars are now ignored by Git; do not
manually delete them from a running database. PostgreSQL does not receive PRAGMAs.

## Providers and enrichment

`SATELLITE_EVENTS_PER_SYNC` defaults to **5** and must be positive. Existing valid
NDVI/acquisition metadata is reused for unchanged event evidence. Material changes
in event location, observation extent/times or detection membership request a new
sample. `refresh_satellite=true` on the sync request explicitly requests a refresh,
subject to the same budget. Failed/deferred context remains eligible for retry.
A failed refresh preserves verified previous values and records
`satellite_refresh_status` / `satellite_refresh_reason` separately.

Timeout defaults in seconds: FIRMS **30**, OSM **20**, Copernicus OAuth **15**,
Copernicus statistics **20**. Requests are sequential and bounded; no unlimited
concurrency is introduced. A satellite enrichment has an outer bound allowing
at most two token/statistics attempts. Budgets and timeouts are independent of
scientific thresholds, classes, feature definitions and model algorithms.

OAuth refresh is protected by a lock and rechecks the cache inside it. Expired
and malformed tokens are not treated as valid. A statistics 401/403 invalidates
only the rejected cached token, obtains a replacement and retries statistics once.
A late rejection cannot invalidate a newer token obtained by another request.
Repeated auth failure returns `provider_auth_failed`. Brief failure caching avoids
simultaneous refresh storms during OAuth outages. Error diagnostics include status
codes or fixed descriptions only, never response bodies or credentials.

Both `http://localhost:3000` and `http://127.0.0.1:3000` are included when either local
origin is configured. The example lists both explicitly; no wildcard is added.
Existing `.env` files were not changed.

## Validation and actual local results

Baseline: pip dependency check and Python compilation passed; **115 backend tests**
and **12 frontend API tests** passed. Frontend typecheck/build initially failed on
copied generated dependency/type files with names such as `react 2` and
`cache-life.d 2.ts`. Reinstalling from the unchanged lockfile with
`npm --prefix frontend ci --ignore-scripts --offline`, followed by a production
build, regenerated these files. No frontend source or package manifest changed.

Final: **143 backend tests** (28 new regressions), **12 frontend API tests**,
Python compilation, pip dependency check, frontend typecheck and production build
passed. Two existing Starlette deprecation warnings remain. Tests use isolated
SQLite databases and mocked providers; no tests train the model or call real APIs.
New regressions cover SQLite PRAGMAs, a second writer during a provider await,
shared sync/backfill exclusion, rollback/recovery after event UPDATE failure,
unchanged-event UPDATE suppression, idempotency and acknowledgements, post-commit
SMTP, cached/deferred/failed satellite context, bounded provider failures, token
expiry/concurrency/auth retries, configuration validation and CORS.

Authenticated real-mode checks returned HTTP 200 for `/health`, login, `/auth/me`,
`/model/status`, `/events`, `/firms/status`, both sync calls and subsequent
`/events`/`/alerts` reads. The real FIRMS query used a conservative Hazira window:
`bounds=[72.5,21.0,72.8,21.2]`, `days=1`.

| Measure | First repaired sync | Second repaired sync |
|---|---:|---:|
| HTTP status | 200 | 200 |
| Client wall seconds | 14.127 | 9.040 |
| Server duration seconds | 14.125 | 9.038 |
| New detections | 0 | 0 |
| Events | 33 | 33 |
| Updated events | 6 | 0 |
| Unchanged events | 27 | 33 |
| OSM requests attempted | 0 | 0 |
| Satellite requests attempted | 5 | 5 |
| Events deferred by budget | 6 | 6 |
| Alerts after sync | 0 | 0 |

All **22 valid satellite contexts were reused**. The five retried events had no
available Sentinel-2 observations; retrying these is intentional, not repeated
fetching of valid cached context. Six missing contexts were deferred by the
budget. Failed-first events may consume the budget again on subsequent runs;
this compact implementation has no fair-rotation scheduler or retry backoff for
missing imagery. The second sync changed no event payloads and duplicated no rows.

A numeric duration for the original failing implementation was not measured.
The supplied failure is the before-state evidence; the numbers above are actual
post-fix measurements, not a claimed benchmark speedup.

## Data, model and security

All **121 detection IDs** and **33 event IDs** matched the pre-integration snapshot.
Candidate CSV, published reviewed-label CSV, model artifact and model metadata
hashes remained exactly unchanged. No real data was deleted, no label changed,
and no model was retrained. The existing trained model remained available.

`git ls-files` confirmed that `backend/.env`, `frontend/.env.local`, the root database
and the backend database were not tracked. No Git-history rewrite or automatic
commit was performed. This check covers the current index, not all historical
commits. The smoke test kept credentials/JWT out of output and report files.

## Files changed

- `backend/app/main.py`: staged processing, ingestion guard, context reuse/budget,
  alert delivery timing, safe operational errors and counters.
- `backend/app/database.py`: SQLite engine setup and dependency rollback.
- `backend/app/providers.py`: timeout limits, single-flight token refresh, one auth
  retry and safe diagnostics.
- `backend/app/config.py`, `backend/.env.example`: budgets, timeouts and local CORS.
- `backend/tests/test_runtime_reliability.py`: 28 regression cases.
- `.gitignore`: SQLite WAL/SHM sidecars.
- This report.

The tested SQLite URL is relative (`sqlite:///./thermaguard.db`). Start from the
repository root to use the verified database, or deliberately configure an absolute
SQLite path. Launch one worker:

```sh
cd /Users/chandankumarmahato/Desktop/SIH2026
PYTHONPATH=backend ./.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Do not start a second backend from another directory and assume it uses the same
SQLite file. The running validation server was started from the repository root.

## Remote Ollama and subscriber SMTP — 12 September 2026

The existing Copilot HTTP client now targets the configured network base URL. It accepts a root, trailing slash, `/api`, or `/api/chat` suffix and emits exactly one `/api/chat` endpoint. `OLLAMA_API_KEY` becomes a Bearer header only when present; credential-bearing URLs, query strings and authenticated non-local plain HTTP are rejected. Local HTTP without a key remains supported. Redirects are not followed. The timeout is configurable. HTTP errors (including 401/403/410/429/5xx), connection/timeout errors, invalid JSON and missing/empty content all retain the existing `deterministic_fallback` contract.

Only an explicitly selected, authorized event is sent to Copilot. Its packet is copied and allowlisted: selected ID, coordinates, ML classification/confidence, deterministic risk, FRP/thermal values, sources/sensors, times and available OSM/NDVI/history. No raw provider credentials or unrelated event records are included. Overview questions use the existing deterministic summary without a remote request. The prompt treats record/user text as data, distinguishes measurements from model interpretation, requires missing evidence to be identified, and forbids fabricated causes, casualties, damage or emergency actions. The model receives no tools and cannot update events, risk, classification or labels.

### Environment configuration

`backend/.env.example` documents remote defaults and placeholders. Fill required fields before enabling each service; disable it explicitly while unavailable. Startup validates enabled configurations, and remote missing-key warnings contain no credentials. Safe health status exposes enabled/configured/mode and whether authentication is configured, never a key.

| Variable | Purpose |
|---|---|
| `OLLAMA_ENABLED` | Enable remote explanations; false retains deterministic Copilot |
| `OLLAMA_BASE_URL` | Network root, e.g. `https://ollama.com` |
| `OLLAMA_API_KEY` | Bearer credential; required by Ollama cloud, optional for compatible local servers |
| `OLLAMA_MODEL` | Exact model available to the configured account; no model is guessed |
| `OLLAMA_TIMEOUT_SECONDS` | Default 30, maximum 120 seconds |
| `SMTP_ENABLED` | Explicit email opt-in at service level |
| `SMTP_HOST`, `SMTP_PORT` | Gmail: `smtp.gmail.com`, `587` |
| `SMTP_USER`, `SMTP_FROM` | Configured sender account, intended `thermaguardAI@gmail.com` |
| `SMTP_PASSWORD` | Google App Password, not the normal Gmail password |
| `SMTP_TIMEOUT_SECONDS` | Default 20, maximum 120 seconds |
| `SMTP_TEST_RECIPIENT` | Optional diagnostic recipient; falls back to sender account |
| `ALERT_RISK_THRESHOLD` | Default 80; accepts legacy `AUTO_ALERT_RISK_THRESHOLD` alias |
| `DEFAULT_ALERT_RADIUS_KM` | Default 10 km when a subscriber has no personal radius |

The existing persisted admin threshold still takes precedence over the environment default. This preserves current administrative controls and deterministic risk logic. Existing `.env` content was retained byte-for-byte as a prefix; only missing nonsecret SMTP enable, timeout and default-radius settings were appended. Keys/passwords were not changed. `backend/.env` remains untracked and ignored.

Official references: [Ollama cloud API](https://github.com/ollama/ollama/blob/main/docs/cloud.mdx) and [Google SMTP/STARTTLS guidance](https://support.google.com/mail/answer/7104828?hl=en).

### Subscriber flow and database safety

Organization dashboard alerts remain unchanged. Email uses user subscriptions rather than broadcasting to organization inboxes. An additive, idempotent SQLite migration adds nullable latitude/longitude/radius and `notifications_enabled=false` to existing users. Users must opt in through authenticated `GET`/`PUT /api/v1/auth/notifications`:

```json
{"notifications_enabled":true,"latitude":22.0,"longitude":70.0,"alert_radius_km":10}
```

These coordinates are an API-format example only; no production subscription was seeded. Enabling requires valid coordinates/email. Missing radius uses the configured default; invalid, non-finite or non-positive radii are rejected. Delivery requires a valid opted-in user inside the Haversine radius **and** existing event-access authorization. No email is sent for demo events or below-threshold events.

The flow is: persist clustered events and dashboard alerts → commit → select eligible users → commit a unique notification attempt → SMTP outside every DB transaction → record safe delivery status in a new short transaction. Existing async ingestion runs this blocking work with `asyncio.to_thread`; synchronous admin routes run in FastAPI's worker pool. WAL, busy timeout and one-worker guidance remain intact.

The small `email_notifications` table is necessary because the existing alert uniqueness is organization-level. It stores event/user/severity/channel uniqueness, a detached evidence snapshot, safe status/error and sent time. Immutable event IDs are retained for audit even when clustering later changes IDs; overlapping detection IDs suppress equivalent sends after reclustering. One event with many FIRMS detections still produces at most one applicable notification per subscriber/severity. Different severity levels can produce distinct notifications.

The durable `attempting` claim is committed before SMTP. Failed or uncertain attempts are not automatically retried, avoiding repeated/spam sends and duplicates following a process crash. This MVP provides at-most-once attempts, not guaranteed exactly-once mail delivery. An `attempting` row after a crash needs operator investigation; do not blindly resend. Multiple independent ingestion processes are still unsupported with SQLite.

SMTP uses EHLO → certificate-verified STARTTLS → EHLO → login → one message. Authentication, connection and send errors are logged as fixed messages without SMTP response bodies, AUTH payloads or credentials. Future authentication diagnostics also expose the numeric SMTP status safely (e.g. 535). Email failures do not roll back core processing. Messages distinguish satellite-derived thermal risk from a confirmed cause and include the non-official-emergency-warning disclaimer.

### Diagnostics and observed results

Both diagnostic routes require administrator authentication:

- `POST /api/v1/admin/diagnostics/ollama`: a harmless connectivity prompt; returns HTTP status, elapsed seconds, model, reachability and response status, never answer text or API credentials.
- `POST /api/v1/admin/diagnostics/smtp`: attempts one test message to `SMTP_TEST_RECIPIENT` or `SMTP_FROM`. Does not create fake events, users or alert records. Call only when intending to send that message.

Observed manual results using the existing `.env`:

| Check | Result |
|---|---|
| Remote Ollama | `https://ollama.com/api/chat`, model `glm-4.6`, HTTP **410**, **0.506 seconds**, reachable=true, response_ok=false |
| Gmail SMTP | Authentication rejected; no message accepted. Numeric status was not retained by the first diagnostic; safe numeric reporting was added afterward, without another authentication attempt |
| Local selected-event fallback | Remote I/O disabled in the temporary diagnostic process; `deterministic_fallback`, nonempty answer, selected event only, original event unchanged |
| Real-event remote check | Automatic approval review blocked transmitting location/sensor/risk evidence to the external model; no event packet was sent by that check |
| User subscriptions | 0 opted-in production users; no production notification rows created |

Remaining manual configuration: verify/change `OLLAMA_MODEL` to a model supported by the account/endpoint, and replace `SMTP_PASSWORD` with a valid Google App Password for `SMTP_USER`. The Ollama key is present, but HTTP 410 is not proof of successful model inference. Do not change unrelated code or guess replacement models to work around provider configuration. A user must separately opt into nearby alerts with their own coordinates. No existing user was enrolled automatically.

### Validation and files

Modified for this task: `backend/app/config.py`, `backend/app/database.py`, `backend/app/main.py`, `backend/.env.example`, `backend/tests/test_remote_services.py` (new, mocked), `backend/tests/test_runtime_reliability.py`, `backend/tests/test_system.py`, `README.md`, and this document. The untracked real `.env` received only missing nonsecret settings. Frontend source, RandomForest, risk logic, reviewed data and model artifacts were not changed by this task.

- Backend suite: **246 passed**, including 52 added cases over the 194-test baseline; existing Starlette deprecation warnings remain. Tests cover remote URL/auth, single-event packets, immutable core evidence, all failure fallbacks, configuration validation, SMTP/TLS/auth failures and safe logging, radius/subscription filtering, threshold/demo isolation, post-commit delivery, schema migration and duplicate protection.
- Frontend API: **12 passed** via `node --test frontend/tests/api.test.mjs`.
- Typecheck and production build: passed; no standalone frontend lint/test npm script exists.
- `./.venv/bin/python -m compileall -q backend`: passed.
- Project venv `pip check`: no broken requirements.
- `git ls-files backend/.env`: no output.
- Model files and both canonical review CSV hashes match the pre-task snapshot.
- Additive migration preserved all prior core rows: 800 detections (including demo), 409 events (including demo), 5 alerts and 3 users.

No retraining, labels, fabricated evidence, commits or pushes were performed. External service success remains blocked by the configured model response and Gmail authentication, while core processing and deterministic fallback remain usable.

Working-tree inspection at completion: `git diff --stat` showed 68 tracked files changed, 3328 insertions and 8280 deletions across this and earlier work. Full status contained 99 entries, including 31 untracked entries. The runtime document and two relevant test files are untracked, so tracked diff statistics exclude them. Thirty-two older review-packet deletions appeared outside this task's edits; they were not restored or otherwise modified. No packet deletion command was issued for the remote AI/SMTP implementation.

## Gemini Copilot migration — 12 September 2026

The Copilot provider was migrated from Ollama (local/remote HTTP chat) to the internet-hosted Google Gemini API using the current `google-genai` SDK (`from google import genai`). The change is provider-internal: routes, request/response contracts, the deterministic fallback, and the single-event allowlisted evidence packet are unchanged. The copilot answer mode is now `gemini` (previously `ollama`) on success and `deterministic_fallback` on any failure, as before.

### Implementation

- `app/main.py`: `gemini_request()` runs the synchronous SDK call through `asyncio.to_thread` so the event loop is never blocked; the route releases its database session before network I/O (`db.rollback()` before the request), so SQLite transactions are never held open while waiting on Gemini. One client instance is reused across requests and rebuilt only when the key or timeout changes. `generate_content` is called with a `system_instruction`-carrying config, so the copilot rules and the JSON evidence packet travel as separate system/user content rather than one concatenated string.
- Failure categories map SDK and network exceptions to safe reasons: `disabled_or_unconfigured`, `authentication_failed` (401), `permission_denied` (403), `quota_or_rate_limited` (429), `provider_error` (5xx and other API errors), `timeout`, `network_error`, `empty_response` (including safety-filtered responses, which expose no text), and `unexpected_error`. The route-level call is additionally guarded so an escaped provider exception cannot produce an HTTP 500; it degrades to the deterministic fallback. No reason string, log line, or response ever contains the API key.
- `app/config.py`: `GEMINI_ENABLED` / `GEMINI_API_KEY` / `GEMINI_MODEL` / `GEMINI_TIMEOUT_SECONDS` (1–120 s) replace the Ollama settings. Startup validation rejects `GEMINI_ENABLED=true` without a key and model. The key field is excluded from `repr`/logs, and `Settings.hide_input_in_errors` remains enabled.
- Diagnostic: `POST /api/v1/admin/diagnostics/gemini` (admin-only, replaces the Ollama diagnostic). It sends the fixed harmless prompt `Reply exactly: THERMAGUARD GEMINI OK`, no event evidence, and returns provider/enabled/configured/reachability/model/timing only — never the key or the answer text.

### Environment

| Variable | Purpose |
|---|---|
| `GEMINI_ENABLED` | Enable Gemini explanations; false retains deterministic Copilot |
| `GEMINI_API_KEY` | Google AI Studio API key; required when enabled; never logged or returned |
| `GEMINI_MODEL` | Exact Gemini model id, e.g. `gemini-2.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Default 30, maximum 120 seconds |

The old `OLLAMA_ENABLED`, `OLLAMA_BASE_URL`, `OLLAMA_API_KEY`, `OLLAMA_MODEL`, and `OLLAMA_TIMEOUT_SECONDS` entries in the untracked `backend/.env` are now unused by code and can be removed manually.

### Verification (measured 12 September 2026)

- Backend suite: **251 passed** (from a 248-test pre-migration baseline) in both default and standalone-file orders; no real Gemini calls occur in unit tests — the provider is mocked at the SDK boundary.
- `python -m compileall backend`: passed. `pip check`: no broken requirements. `google-genai` 2.23.0 added to `backend/requirements.txt` (already present in the project venv).
- Frontend: typecheck passed, production build passed, API client tests **12 passed**; the served bundle contains Gemini wording and zero Ollama references.
- Live diagnostic: `response_ok=true`, model `gemini-3.8-flash`, **3.755 s** elapsed. Live single-event copilot chat returned `mode=gemini` with an evidence-grounded answer referencing the selected event ID only.
- Database safety: the `/api/v1/events` payload was captured before and after both live Gemini calls and compared byte-for-byte — identical. Classification, risk, labels and review data are untouched; no retraining occurred; no model artifacts, reviewed CSVs or event records were modified.
- Security: `git ls-files backend/.env` is empty; the configured Gemini key value appears in zero tracked files; no `AIza…`-pattern key exists in tracked content.

The previous "Remote Ollama and subscriber SMTP" section above is retained as a dated historical record of the earlier architecture.


### Copilot question and overview fix

Copilot now includes the user's question in the Gemini request alongside allowlisted evidence. A selected event sends one record; overview requests send at most ten highest-risk records from the user's authorized scope. Empty scopes remain local. Provider failures retain the factual fallback and return a sanitized reason for the UI. HTTPX transport errors from the Gemini SDK are categorized as timeout/network failures. This supersedes the earlier single-event-only and deterministic-overview behavior.
