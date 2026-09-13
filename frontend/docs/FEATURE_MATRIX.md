# ThermaGuard frontend feature matrix

Backend APIs are immutable. No backend files are changed. Categories: **1** Existing + improve UI; **2** Existing but incomplete; **3** Frontend-only derivation; **4** Requires future backend API; **5** Post-hackathon feature. Multiple categories distinguish working portions from unsupported portions.

| # | Feature | Status | Existing endpoint | Frontend component | Backend change required? | Current limitations |
|---|---|---|---|---|---|---|
|1|Review and training data|1,3,4|GET /model/review-candidates; /model/review-readiness|ReviewCenter; IntelligenceWorkspace|Only for writes/diffs|Read-only rank, class balance, counts, metadata completeness; no authoritative health score|
|2|Active learning|3,4|GET /events; /model/review-candidates|derived/intelligence rankCandidates|For training-relative novelty/disagreement|Transparent local priority; no labels; no reference dataset invented|
|3|Explainable AI|1,4|GET /events; /events/{id}/evidence|EventIntelligence|For local attributions|Existing measurements/probabilities and reasons; no SHAP or fabricated causal support/contradiction|
|4|Event timeline|3,4|GET /events; /alerts; /model/review-candidates|EventIntelligence|For versioned update history|Only supplied detection/context/alert/delivery/review timestamps|
|5|Sensor provenance|1|GET /events|EventIntelligence; EventTable|No|Displays source_counts and supplied summary; unknown satellite/instrument fields remain unavailable|
|6|Event quality|3|GET /events|derived/intelligence completeness|No|Eight equal-weight presence checks; distinct from model confidence, not authoritative|
|7|Facility intelligence|2,4|GET /events context|EventIntelligence|For facility-linked histories/IDs|Existing nearby names and industrial distance only; no facility coordinates invented|
|8|Historical hotspots|3,4|GET /events; /events/{id}/history|IntelligenceWorkspace; MapView|For long-term density history|Persistent-location map/table uses persistence ≥2 days; no synthetic heatmap|
|9|Event lifecycle|2,4|GET /events status|EventIntelligence; futureCapabilities|For writes|Reported state shown; eight proposed states never assigned from risk alone|
|10|Operations|1,4|POST /alerts/{id}/acknowledge; existing admin endpoints|AlertCenter; NotificationSettings; IntelligenceWorkspace|For owner/notes/checklist/resolution|Existing acknowledgement retained; unsupported actions disabled|
|11|Environmental impact|1|GET /events context|EventIntelligence; ContextPanel|No|Provider status, measurements, timestamp, age and attribution; no dispersion model|
|12|Wind-aware UI|3|GET /events weather|MapView|No|Downwind direction only when available; no spread prediction|
|13|Geofencing|1|GET /admin/assignments; /auth/notifications|NotificationSettings; IntelligenceWorkspace; MapView|No|Admin assignment visibility and subscriber radius; no new backend authorization|
|14|Watchlists|3,4|None for persistence|IntelligenceWorkspace|For cross-device/facility/region sync|Account-keyed local event IDs only, current authorized scope; session fallback if storage fails|
|15|Alert intelligence|1,2,4|GET /alerts|AlertCenter; EventIntelligence; Operations|For fields absent from response|Existing channel status/timestamps; no guessed recipients/failure reasons/dedup state|
|16|Provider reliability|1|GET /providers/status|ProviderHealthGrid; System Status|No|Process-local telemetry, not provider uptime history|
|17|Model operations|1,4|GET /model/status; /model/metrics|ModelView; futureCapabilities|For history/rollback/shadow|Real metrics; disabled optional version operations|
|18|Drift monitoring|3,4|GET /events|IntelligenceWorkspace History & trends|For formal baseline drift|Last-observed-date cohorts: FRP/confidence/missing checks; no statistical drift claim|
|19|Data lineage|3,4|GET /events; /alerts; /model/review-candidates|EventIntelligence|For per-stage audit|Known stages shown; validation/dedup/update and dataset inclusion remain unverified|
|20|Copilot modes|1|Existing POST /copilot/chat|IntelligenceWorkspace; CopilotModal|No|Seven evidence prompts, selected event context; existing Gemini/fallback behavior preserved|
|21|Natural-language search|3|None; loaded /events data|derived/intelligence naturalSearch|No|Four explicit patterns; unsupported text rejected locally; refinery-name matching is qualified|
|22|Reports|3|Existing event/provider/model/review data|IntelligenceWorkspace; ModelView|No|Six print-friendly reports; browser print, not server PDF generation; loaded-scope limitations stated|
|23|Analytics|1,3|GET /analytics/trends; /events; /alerts|AnalyticsView; IntelligenceWorkspace|For complete longitudinal telemetry|Existing trends/distributions retained; new cohort and diversity tables|
|24|Map layers|1,3,4|GET /events; /eonet/events; event context|MapView|For unsupported geometries/history|Events, selected, risk, persistent, assigned bounding boxes, recorded alert coordinates, hazard/context/radius; no fake industrial polygons or density|
|25|Security UI|1|GET /auth/me; backend authorization|page; IntelligenceWorkspace|No|Role/org/scope visible; protected access remains backend-enforced|
|26|Audit/transparency|3,4|Existing timestamp fields|EventIntelligence; System Status|For full history|No invented actor/change or classification update times|
|27|PWA/mobile|3,2|No new API|manifest.ts; firebase-messaging-sw.js|No|Install manifest; offline shell only after existing opt-in worker activation; browser install support varies|
|28|Data freshness|1,3|Existing provider timestamps|EventIntelligence; System Status; ContextPanel|No|Age only with valid timestamp; future times flagged, absent dates unknown|
|29|Event comparison|3|Loaded /events|IntelligenceWorkspace|No|2–4 events, visible fields, no cross-scope fetch|
|30|Similar events|4,5|None|Future workflows|For ML similarity|Explicit unavailable interface; no false ML similarity score|
|31|Resolution feedback|4|None|Future workflows|Yes, optional|Visual flow only; resolution never auto-creates ground truth|
|32|Reviewer disagreement|4|None|Future workflows|Yes, optional|Reviewer A/B, senior review and consensus described; no fabricated records|
|33|Label quality|1,4|GET /model/review-candidates|ReviewCenter; Review intelligence|For unsupported fields/writes|Supplied metadata only; no inferred reviewer confidence|
|34|System command center|3|GET /providers/status; /model/status; /firms/status; /alerts|IntelligenceWorkspace System Status|No|Consolidated current records; missing telemetry explicit|
|35|Judge mode|3|Existing records|Reports & judge mode|No|Selected event lineage/evidence, actual data labels, failure visibility and links to metrics/review; no fake live video|

Endpoint paths in the table are relative to `/api/v1`. Optional proposed contracts, never called by runtime code, are typed in `frontend/lib/adapters/futureCapabilities.ts`:

| Proposed endpoint | Purpose |
|---|---|
|GET /api/v1/model/training-reference|Versioned region/sensor/class reference for novelty and coverage|
|GET /api/v1/events/{id}/similar|Method/version-qualified similarity results|
|PUT /api/v1/events/{id}/review|Human review with evidence-version concurrency|
|GET /api/v1/events/{id}/evidence-diff|Versioned evidence differences|
|PUT /api/v1/events/{id}/lifecycle|Explicit owner/state/notes transition|
|PUT /api/v1/events/{id}/response|Checklist, escalation and resolution|
|GET /api/v1/facilities/{id}/events|Facility geometry/type and linked histories|
|PUT /api/v1/auth/watchlist|Cross-device event/facility/region watchlist|
|GET /api/v1/model/versions|Experiments and model-version registry|
|POST /api/v1/model/rollback|Audited rollback with expected version|
|GET /api/v1/model/shadow-results|Version-qualified comparison predictions|
|GET /api/v1/model/drift|Reference/current windows, statistics and thresholds|
|GET /api/v1/events/{id}/explanation|Method-qualified feature attributions|
|GET /api/v1/events/{id}/audit|Versioned timestamp/actor/change records|
|GET /api/v1/events/{id}/reviews|Multiple reviews and consensus|
|POST /api/v1/events/{id}/outcome|Source-backed outcome verification|

These are proposals, not additions to or promises about the backend contract. Server-side authorization, validation, concurrency and audit requirements would need separate design approval.
