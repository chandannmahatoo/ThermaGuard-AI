# FIRMS Runtime Reliability Repair

## Confirmed cause

The previous `process()` inserted and flushed detections before awaiting OSM and Copernicus, then updated/flushed events repeatedly and committed only at the end.

An SQLite writer could therefore remain reserved throughout slow network calls. Concurrent synchronization or an unrelated writer could exhaust SQLite's previous short default wait and raise:

```text
OperationalError: database is locked
```

Successful satellite context was fetched repeatedly, and a failed refresh could erase it. SMTP was also performed before the alert transaction committed.

---

## Transaction and concurrency changes

1. **Short initial ingestion transaction**  
   Normal ingestion stores deduplicated detections in a short initial transaction. It then copies detection/event evidence into dictionaries and releases the read transaction. If later event persistence fails, valid acquired detections remain available for the next full rebuild.

2. **No write transaction across provider calls**  
   Clustering, bounded provider calls, classification and risk run on detached dictionaries. No database write transaction is held across provider awaits.

3. **Controlled persistence phase**  
   Persistence reserves the SQLite writer with `BEGIN IMMEDIATE` before checking the snapshot, batches changed/new event payloads, migrates alert identities, and commits. Unchanged events are not assigned new payloads. Flushes occur at batch foreign-key boundaries rather than once per event. Removed-parent cases require an extra flush to move/delete referencing alerts before deleting old event rows.

4. **SMTP after commit**  
   SMTP delivery occurs after the alert/event commit, with a separate short transaction for its outcome. No SMTP request runs while holding the event write transaction.

> This MVP notification flow is not a durable message-delivery worker. A crash after commit may leave an `email_pending` or `attempting` state that requires operator inspection.

### Offline review acquisition path

The offline human-review acquisition path remains special:

```text
commit=False
```

requires:

```text
enrich=False
notifications disabled
```

This keeps the batch atomic so reviewed snapshots can be checked and the entire batch rolled back. It makes no live provider calls inside `process()`.

### Synchronization guard

Current sync and historical backfill share one application-level `asyncio.Lock`.

An overlapping operation receives:

```text
409: FIRMS synchronization already in progress
```

The guard covers FIRMS fetching and the full ingestion run.

Database operational errors roll back the session and return:

```text
503: Database temporarily busy; retry synchronization.
```

SQL parameters, event payloads, tokens and provider error bodies are not logged. Request dependencies also roll back on exceptional exit.

### Important SQLite operating rule

Run SQLite with **one application worker/process**.

The synchronization guard is process-local. Independent CLI tools, reload processes and multiple worker processes do not share it. Snapshot checks reject stale computation, but they do not provide distributed coordination.

Do not run acquisition CLIs and live synchronization simultaneously.

SQLite can still return the controlled `503` if another writer holds the database past the configured timeout. This is resilience, not a claim that contention is impossible.

---

## SQLite configuration

Only SQLite engines receive:

- connection `timeout=30`
- `check_same_thread=False`
- `foreign_keys=ON`
- `journal_mode=WAL`
- `busy_timeout=30000`

`FULL` synchronous durability is retained; `NORMAL` is not enabled.

The verified local database configuration reported:

- WAL enabled
- foreign keys enabled
- 30,000 ms busy timeout
- synchronous value `2`

SQLite WAL/SHM sidecars are ignored by Git.

> Do not manually delete WAL/SHM files from a running database.

PostgreSQL does not receive SQLite PRAGMAs.

---

## Providers and enrichment

`SATELLITE_EVENTS_PER_SYNC` defaults to:

```text
5
```

and must be positive.

Existing valid NDVI/acquisition metadata is reused for unchanged event evidence.

Material changes in:

- event location
- observation extent
- event times
- detection membership

can request a new sample.

`refresh_satellite=true` explicitly requests a satellite refresh, subject to the same per-sync budget.

Failed/deferred context remains eligible for retry.

A failed refresh preserves previously verified values and records:

```text
satellite_refresh_status
satellite_refresh_reason
```

separately.

### Provider timeout defaults

| Provider operation | Timeout |
|---|---:|
| FIRMS | 30 s |
| OSM | 20 s |
| Copernicus OAuth | 15 s |
| Copernicus statistics | 20 s |

Requests are sequential and bounded. No unlimited provider concurrency is introduced.

A satellite enrichment has an outer bound allowing at most two token/statistics attempts.

Budgets and timeouts are independent of scientific thresholds, model classes, feature definitions and model algorithms.

### Copernicus OAuth safety

OAuth refresh is protected by a lock and rechecks the cache while holding that lock.

Expired or malformed tokens are not treated as valid.

A statistics `401`/`403`:

1. invalidates only the rejected cached token,
2. obtains a replacement,
3. retries statistics once.

A late rejection cannot invalidate a newer token acquired by another request.

Repeated authentication failure returns:

```text
provider_auth_failed
```

Brief failure caching reduces simultaneous token-refresh storms during provider outages.

Error diagnostics expose safe status codes or fixed descriptions only; response bodies and credentials are not returned.

### Local CORS

When either local frontend origin is configured, both are supported:

```text
http://localhost:3000
http://127.0.0.1:3000
```

No wildcard origin is added.

Existing `.env` files are not automatically replaced.

---

## Validation and measured local results

### Initial validation

The following passed during the reliability repair:

- Python dependency check
- Python compilation
- **115 backend tests**
- **12 frontend API tests**

Frontend typecheck/build initially encountered copied generated dependency/type files with names such as:

```text
react 2
cache-life.d 2.ts
```

Reinstalling dependencies from the unchanged lockfile using:

```bash
npm --prefix frontend ci --ignore-scripts --offline
```

and rebuilding regenerated the affected generated files.

No frontend source or package manifest change was required for that repair.

### Final validation for the FIRMS reliability repair

- **143 backend tests passed**
- **12 frontend API tests passed**
- Python compilation passed
- `pip check` passed
- frontend typecheck passed
- production frontend build passed
- two pre-existing Starlette deprecation warnings remained

Tests use isolated SQLite databases and mocked providers. They do not train the model or prove current live-provider availability.

New regression coverage included:

- SQLite PRAGMAs
- second writer during provider await
- sync/backfill mutual exclusion
- rollback/recovery after event update failure
- unchanged-event update suppression
- idempotency
- alert acknowledgements
- post-commit SMTP
- cached/deferred/failed satellite context
- bounded provider failures
- token expiry/concurrency/auth retry
- configuration validation
- CORS

### Real-mode smoke checks

Authenticated real-mode checks returned HTTP `200` for:

- `/health`
- login
- `/auth/me`
- `/model/status`
- `/events`
- `/firms/status`
- synchronization calls
- subsequent event/alert reads

The real FIRMS query used a conservative Hazira window:

```json
{
  "bounds": [72.5, 21.0, 72.8, 21.2],
  "days": 1
}
```

### Repaired-sync measurements

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

All **22 valid satellite contexts were reused**.

The five retried events had no available Sentinel-2 observations. Retrying them is intentional and is not repeated fetching of already valid cached context.

Six missing contexts were deferred by the budget.

Failed-first events may consume the budget again on later runs. The current compact implementation does not include a fair-rotation scheduler or retry backoff for unavailable imagery.

The second synchronization changed no event payloads and produced no duplicate rows.

A numeric duration for the original failing implementation was not measured. The pre-fix failure is the before-state evidence; the measurements above are post-fix observations, not a claimed benchmark speedup.

---

## Data, model and security integrity

During the FIRMS reliability repair:

- all **121 detection IDs** matched the pre-integration snapshot,
- all **33 event IDs** matched the pre-integration snapshot,
- review candidate CSV hash remained unchanged,
- reviewed-label CSV hash remained unchanged,
- model artifact hash remained unchanged,
- model metadata hash remained unchanged,
- no real data was deleted,
- no label was changed,
- no model was retrained.

`git ls-files` confirmed that the following were not tracked:

```text
backend/.env
frontend/.env.local
local database files
```

No Git-history rewrite or automatic commit was performed.

This check applies to the inspected Git index/state and should not be interpreted as a complete audit of every historical commit.

---

## Files changed for the FIRMS reliability repair

- `backend/app/main.py`
  - staged processing
  - synchronization guard
  - context reuse/budget
  - alert-delivery timing
  - safe operational errors
  - counters

- `backend/app/database.py`
  - SQLite engine setup
  - dependency rollback

- `backend/app/providers.py`
  - provider timeout limits
  - single-flight token refresh
  - one authentication retry
  - safe diagnostics

- `backend/app/config.py`
  - provider budgets
  - timeout configuration
  - local CORS configuration

- `backend/.env.example`
  - documented settings only

- `backend/tests/test_runtime_reliability.py`
  - reliability regression coverage

- `.gitignore`
  - SQLite WAL/SHM sidecars

- runtime reliability documentation

### Verified startup location

The tested SQLite URL is relative:

```text
sqlite:///./thermaguard.db
```

Start the backend from the repository root to use the intended database:

```bash
cd /Users/chandankumarmahato/Desktop/SIH2026

PYTHONPATH=backend ./.venv/bin/python -m uvicorn \
  app.main:app \
  --host 127.0.0.1 \
  --port 8000
```

Do not start a second backend from another directory and assume it uses the same relative SQLite file.

---

# Subscriber Email Alerts

> The following notification work remains relevant. The older Ollama-specific Copilot details later in this document are retained only as historical context and have been superseded by the Gemini migration section.

## Subscriber flow and database safety

Organization dashboard alerts remain unchanged.

Email delivery uses user subscriptions instead of broadcasting to organization inboxes.

An additive, idempotent SQLite migration adds nullable:

```text
latitude
longitude
radius
notifications_enabled
```

to existing users, with notifications disabled by default.

Users opt in through authenticated notification settings.

Example API payload:

```json
{
  "notifications_enabled": true,
  "latitude": 22.0,
  "longitude": 70.0,
  "alert_radius_km": 10
}
```

These coordinates are an API-format example only; no production subscription is implied.

Enabling notifications requires:

- valid coordinates
- valid email
- positive finite radius when supplied

When no personal radius is provided, the configured default applies.

Delivery requires:

1. a valid opted-in user,
2. user inside the Haversine alert radius,
3. existing backend event-access authorization,
4. non-demo event,
5. threshold-eligible event.

### Delivery flow

```text
persist event
→ persist dashboard alert
→ commit
→ find eligible subscribers
→ commit unique notification attempt
→ SMTP outside DB transaction
→ record delivery outcome in a short transaction
```

The small `email_notifications` table exists because dashboard-alert uniqueness is organization-level while email uniqueness is user-level.

It stores:

- event/user/severity/channel uniqueness
- detached evidence snapshot
- safe status/error
- sent timestamp

Immutable event IDs remain available for audit.

Overlapping detection IDs suppress equivalent sends after reclustering.

One event with many FIRMS detections produces at most one applicable attempt per subscriber/severity. A later severity level can create a distinct notification.

### At-most-once behavior

The durable `attempting` claim is committed before SMTP.

Failed or uncertain attempts are not automatically retried. This avoids duplicate/spam delivery after uncertain process failure.

This MVP therefore provides **at-most-once notification attempts**, not guaranteed exactly-once email delivery.

An `attempting` row left by a crash requires operator investigation.

Multiple independent ingestion processes remain unsupported with SQLite.

### SMTP security

SMTP uses:

```text
EHLO
→ certificate-verified STARTTLS
→ EHLO
→ login
→ send one message
```

Authentication, connection and send failures are logged using safe fixed messages without:

- SMTP response bodies
- authentication payloads
- credentials

Email failures never roll back core event processing.

Messages distinguish satellite-derived thermal risk from a confirmed physical cause and include a non-official-emergency-warning disclaimer.

### SMTP environment

| Variable | Purpose |
|---|---|
| `SMTP_ENABLED` | Enable email notification service |
| `SMTP_HOST` | SMTP hostname |
| `SMTP_PORT` | SMTP port; Gmail STARTTLS normally uses 587 |
| `SMTP_USER` | Authenticated sender account |
| `SMTP_FROM` | Message sender address |
| `SMTP_PASSWORD` | App Password / SMTP credential; never normal account password |
| `SMTP_TIMEOUT_SECONDS` | Bounded SMTP timeout |
| `SMTP_TEST_RECIPIENT` | Optional admin diagnostic recipient |
| `ALERT_RISK_THRESHOLD` | Default environment alert threshold |
| `DEFAULT_ALERT_RADIUS_KM` | Default subscriber alert radius |

The persisted administrator threshold still takes precedence over the environment default where implemented.

---

# Historical Ollama Migration Record

> **Historical only — superseded by Gemini.**  
> This section is retained to document an earlier architecture state. Ollama is no longer the active Copilot provider after the Gemini migration described below.

The former Copilot HTTP client supported a configured network Ollama endpoint, optional bearer authentication, URL validation, bounded timeout and deterministic fallback.

The historical implementation preserved the following security principles:

- only authorized event evidence could be sent,
- credentials were excluded from event packets,
- provider failures degraded to deterministic fallback,
- the provider could not modify events, risk, classification or labels,
- diagnostics did not return API keys or answer text.

Historical environment variables included:

```text
OLLAMA_ENABLED
OLLAMA_BASE_URL
OLLAMA_API_KEY
OLLAMA_MODEL
OLLAMA_TIMEOUT_SECONDS
```

These values are now unused by the active Gemini implementation and may be removed manually from the untracked local environment after confirming no other tooling depends on them.

Historical provider checks and results should not be interpreted as current system status.

---

# Gemini Copilot Migration — 12 September 2026

The Copilot provider was migrated from Ollama to the internet-hosted **Google Gemini API** using the current `google-genai` SDK:

```python
from google import genai
```

The migration is provider-internal.

The following remain stable:

- API route contracts
- request/response structure
- deterministic fallback
- evidence allowlisting
- authorization boundaries
- classification ownership
- risk ownership
- review ownership

Successful Copilot responses use:

```text
mode=gemini
```

Failures use:

```text
mode=deterministic_fallback
```

---

## Gemini implementation

### Backend behavior

`app/main.py` uses `gemini_request()`.

The synchronous Gemini SDK call runs through:

```python
asyncio.to_thread(...)
```

so network I/O does not block the event loop.

Before remote Gemini I/O, the route releases the database transaction/session state, preventing SQLite transactions from being held open while waiting for the provider.

A Gemini client instance is reused across requests and rebuilt only when the key or timeout configuration changes.

`generate_content` uses a separate system instruction and user/evidence content rather than concatenating all control rules into unstructured text.

### Safe failure categories

Provider and SDK failures map to sanitized categories:

```text
disabled_or_unconfigured
authentication_failed
permission_denied
quota_or_rate_limited
provider_error
timeout
network_error
empty_response
unexpected_error
```

Safety-filtered or empty provider responses expose no fabricated answer text.

The route has an outer defensive fallback so an escaped provider exception does not become a user-visible HTTP 500 when deterministic fallback can safely answer.

No log line, reason string or API response should contain the Gemini API key.

---

## Gemini environment

| Variable | Purpose |
|---|---|
| `GEMINI_ENABLED` | Enable Gemini explanations; disabled mode retains deterministic Copilot behavior |
| `GEMINI_API_KEY` | Google AI API key; required when enabled; never logged or returned |
| `GEMINI_MODEL` | Exact configured Gemini model identifier |
| `GEMINI_TIMEOUT_SECONDS` | Bounded provider timeout |

Startup validation rejects:

```text
GEMINI_ENABLED=true
```

when required key/model configuration is missing.

Legacy Ollama variables are no longer used by the active Copilot path.

---

## Gemini diagnostics

Admin-only endpoint:

```text
POST /api/v1/admin/diagnostics/gemini
```

The diagnostic sends a fixed harmless connectivity prompt and does not send event evidence.

It returns only safe operational information such as:

- provider
- enabled/configured state
- reachability
- model
- elapsed time
- response status

It does **not** return:

- API key
- event evidence
- answer text

---

## Gemini verification measured 12 September 2026

Documented verification reported:

- **251 backend tests passed**
- backend compilation passed
- `pip check` reported no broken requirements
- `google-genai` was available in the project environment
- frontend typecheck passed
- frontend production build passed
- **12 frontend API tests passed**
- served frontend contained Gemini wording and no active Ollama references

The documented live diagnostic reported:

```text
response_ok=true
elapsed=3.755 s
```

The development record listed a configured Gemini model and a successful evidence-grounded selected-event request.

These are dated development observations, not guarantees of current external-service availability.

### Database safety verification

The `/api/v1/events` payload was captured before and after the live Gemini checks and compared byte-for-byte.

The documented result was unchanged.

Gemini does not modify:

- event records
- model classification
- risk
- labels
- review data
- model artifacts

No retraining occurs through the Copilot path.

### Security verification

The development audit reported:

```text
git ls-files backend/.env
```

returned no tracked environment file.

The configured Gemini key did not appear in tracked project content.

---

## Copilot question and overview behavior

The Copilot includes the user's question in the Gemini request alongside allowlisted evidence.

### Selected-event request

A selected event sends one authorized event record.

### Overview request

Overview requests send at most ten highest-risk records from the user's already-authorized scope.

Empty authorized scopes remain local and do not require a remote request.

Provider failures preserve the deterministic factual fallback and return only a sanitized reason to the UI.

HTTP transport errors from the Gemini SDK are classified as timeout/network failures where appropriate.

---

# Final operational rules

## SQLite

For the current MVP:

```text
one backend process
one SQLite writer domain
no concurrent acquisition CLI + live sync
```

## FIRMS ingestion

- use bounded synchronization,
- allow the application lock to serialize sync/backfill,
- retain acquired observations even if later event persistence fails,
- do not hold write transactions across provider requests.

## Provider context

- reuse verified context when evidence is unchanged,
- retry missing/deferred context within configured budgets,
- never erase verified provider evidence because a later refresh fails.

## Notifications

- commit core event/alert state before SMTP,
- treat delivery status separately from event persistence,
- do not blindly resend uncertain attempts.

## Gemini

- use allowlisted authorized evidence only,
- separate system instructions from evidence/user content,
- never let Copilot mutate classification, risk, labels or events,
- sanitize all provider errors,
- preserve deterministic fallback.

---

# Current limitations

This remains a local engineering/hackathon MVP.

Known limitations include:

- SQLite synchronization guard is process-local.
- Multiple independent backend workers are not supported safely with the current SQLite architecture.
- Missing satellite imagery has no fair-rotation retry scheduler.
- Notification delivery is not a durable distributed queue.
- At-most-once notification attempts can require manual operator reconciliation after a crash.
- External provider success depends on credentials, quotas and service availability.
- Dated validation results are not guarantees of present runtime behavior.

For production deployment, migrate concurrency-sensitive persistence and work scheduling to infrastructure designed for multi-process/distributed operation.
