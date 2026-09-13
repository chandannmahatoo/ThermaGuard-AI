# Intelligence feature layer — implementation report

## Outcome

Added **Intelligence Lab** and **System status** to the existing authenticated shell. The previous monitoring, evidence drawer, analytics, model evaluation, review, provider, administration, alerts and Firebase preference/registration flows remain in place. No existing component was removed. Backend files touched: **ZERO**. `git diff -- backend` is empty.

The complete 35-group classification, limitations and proposed future contracts are in FEATURE_MATRIX.md. Its unsupported states are intentional implementations of the immutable-backend rule, not simulated features.

## Implemented tools

- Event intelligence: classification/probabilities/reasons, explicit confidence disclaimer, independent deterministic risk factors, missing evidence, thermal measurements, actual sensor-summary field names, nearby facility names, environmental status/attribution/freshness, supplied timeline timestamps and stage-by-stage lineage.
- UI evidence completeness: eight documented equal-weight presence checks, separate from model confidence. No official quality score or SHAP attribution is invented.
- Review intelligence: transparent priority ranking, class balance, reviewed/backlog counts, metadata-presence percentage, loaded-region and sensor-presence diversity, missing risk-context analysis. Suggested ordering never labels or approves candidates.
- Comparison: two to four loaded authorized events with classification, confidence, risk, FRP, persistence, sensor sources, completeness and baseline availability.
- Local watchlists: account-keyed browser storage containing event IDs only; current-scope rendering and in-memory fallback when storage is unavailable. This does not create notifications or cross-device persistence.
- Four supported natural-language patterns translate to local predicates. Unknown patterns show a limitation and generate no backend request.
- Historical tools: persistent-location map/table and last-observed-date cohorts of FRP/confidence/missing checks. These are not formal statistical drift or an invented density heatmap.
- Operations: current role/organization, available assignment bounds, existing alert coordinates, notification radius and links to supported management/acknowledgement flows.
- Reports: six print-friendly reports, including actual model evaluation via the existing ModelView. Weekly summaries clearly state their loaded-event inventory/window limits.
- Judge walkthrough: selected-event lineage, visible REAL/DEMO counts, provider failures, classification/risk separation and links to evaluation/review/delivery views.
- System Status: ingestion, enrichment, intelligence and delivery telemetry plus model/readiness/alerts/review state.
- Map: downwind context from recorded meteorological direction, with no spread forecast; supported organization bounds and recorded alert locations.
- PWA: install manifest/icon and network-only offline navigation fallback in the existing messaging worker. No API responses, credentials or incident data are cached.

## Unsupported workflows

Typed adapters describe optional endpoints for review writes, evidence diffs, lifecycle/response ownership, facility history, cross-device watchlists, model history/rollback/shadow, drift baseline, local attributions, versioned audits, reviewer consensus, verified outcomes, training-reference novelty and model-based similarity. All return `available: false`; buttons are disabled. Endpoint proposals are documentation only and are never called.

Reviewer confidence, causal evidence support/contradiction, arbitrary lifecycle transitions, automatic outcome-to-label conversion and unavailable timestamps are not inferred. Geographic/sensor novelty against training data requires a versioned reference; current loaded diversity is not misrepresented as that baseline.

## Compatibility and security

The frontend reuses current `apiGet`, event/evidence/history requests and Copilot submission behavior. New Copilot mode buttons prepare an evidence-specific question; submission remains the existing user action. Assignment loading uses the existing admin endpoint and role gating. Backend authorization remains authoritative. The API client, Firebase token helper, notification preferences and all backend files are unchanged by this feature-layer task.

The offline shell becomes available only after the existing opt-in Firebase worker has activated. This task does not request browser permissions or guarantee installation on every browser. Offline navigation offers reconnect/retry; it does not expose stored protected records or support offline mutations.

## UX, accessibility and performance

New views are lazy-loaded. Reused tables, status badges and shared surfaces keep the design consistent. Tabs and comparison inputs have accessible names/states; unavailable actions are disabled; status messages identify scope and limitations. Comparison tables scroll within bounded regions. Print styling excludes navigation and interactive controls. Existing mobile drawer focus management, keyboard support and reduced-motion behavior remain intact.

The new tools were tested at 320, 375, 768, 1024 and 1440px. A long disabled future-action label initially overflowed at 320px; wrapping now prevents it. Existing production main-route first-load JavaScript remains approximately 161 kB, with this workspace in a separate dynamic chunk.

## Validation

- `npm run typecheck`: PASS.
- `npm run build`: PASS, Next.js 15.5.25, including `/manifest.webmanifest`.
- `npm test`: **101 passed**, zero failed.
- `npm run test:e2e`: **22 passed**, zero failed; no uncaught browser errors in the suite.
- Existing and new workspace tools checked at all five requested widths.
- Browser tests cover comparison, local-watch persistence, unsupported search, printable data-mode labels, disabled rollback, plus all previous navigation/auth/model/notification regressions.
- Unit tests cover completeness, ranking, search, timeline, zero/missing trend semantics, freshness, sensor fields, bounds validation, unavailable adapters and the no-cache/no-API-interception offline fallback.
- `git diff --check`: PASS.
- `git diff --exit-code -- backend`: PASS (empty).

E2E uses clearly labeled test-only response fixtures and a nonfunctional token; it does not mutate backend state or send real notifications. Real-provider uptime, real FCM delivery and manual browser installation are not claimed by these checks.

## Files added for this feature layer

- frontend/components/intelligence/IntelligenceWorkspace.tsx
- frontend/components/intelligence/EventIntelligence.tsx
- frontend/lib/derived/intelligence.ts
- frontend/lib/adapters/futureCapabilities.ts
- frontend/app/manifest.ts
- frontend/public/icon.svg
- frontend/docs/FEATURE_MATRIX.md
- frontend/docs/INTELLIGENCE_IMPLEMENTATION.md

## Existing files extended in this feature layer

- frontend/app/page.tsx — view wiring and reuse of existing callbacks/data.
- frontend/app/globals.css — centralized tool, map, print and responsive styling.
- frontend/components/MapView.tsx — recorded wind, assignment bounds and alert positions.
- frontend/public/firebase-messaging-sw.js — network-only offline navigation fallback.
- frontend/tests/experience.test.mjs — new component/derivation coverage.
- frontend/tests/push.test.mjs — existing push tests retained; offline fallback coverage.
- frontend/tests/e2e/workspace.spec.ts — new view, comparison, watchlist and report checks.
- frontend/next-env.d.ts may change automatically between development and production Next.js builds.

The working tree also contains the earlier approved frontend redesign. Those changes were preserved, not reset or recommitted.
