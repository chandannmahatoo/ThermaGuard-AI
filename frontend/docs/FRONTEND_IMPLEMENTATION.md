# ThermaGuard frontend implementation

## Audit and problems found

See FRONTEND_AUDIT.md for the pre-change inventory. Existing features were retained rather than replaced. Main issues were ungrouped navigation, missing mobile focus management, hidden mobile sorting, unknown risk styled as Normal, missing map fit/grouping controls, no dedicated model evaluation, incomplete provider comparison, and no browser test suite. Browser checks additionally found notification action overflow at 320/375px and a stuck login loading state after session expiry.

## Screens and components

- Shell: grouped Overview, Intelligence, Operations and System navigation; collapsible desktop navigation; mobile modal navigation with focus trapping, Escape, backdrop, focus restoration and skip link. Only implemented views appear.
- Overview: added CommandSummary with open-alert and unreviewed-candidate counts, risk/class distributions, and links to existing views. Missing data is labeled. Priority map feed sorts by actual risk score.
- Map: fit-to-results, expandable risk/class legend, grouped dense event views below zoom 11, selected-event isolation, invalid-coordinate rejection. Groups retain original events; supporting rings remain explicitly event-position context rather than fabricated facility locations.
- Events: visible sorting outside the mobile-hidden header, aria-sort, persistence/source fields and event status. Existing pagination, mobile cards and selection are retained. Risk/sensor/age filters persist in the URL; credentials and free-text search do not.
- Providers: eleven-provider comparison table, accessible scrolling, loading/retry and explicit stale telemetry on refresh failure.
- Model: new ModelView consumes the existing GET /model/metrics response through apiGet. It shows availability/readiness, algorithm, validation/test metrics, per-class precision/recall/F1/support, confusion matrices, split counts/groups and feature list. Small/unreported datasets receive a qualification.
- Review: read-only export queue exposes supplied label/review state, reviewer/reference, split group, timestamp/notes when present. No fake save, approval, or review-write request.
- Settings/notifications: narrow-screen action wrapping and bounded inputs; retryable load failure replaces endless loading. Existing saved-preference and browser-push registration behavior remains intact.
- Authentication: session-expiry now clears frontend busy state so reauthentication is possible. Backend authentication and token format/storage remain unchanged.

Created components: CommandSummary, ModelView. MapTools and EventMarkers are internal reusable map components. Added pure mapGrouping helper and read-only ReviewCandidate type. Removed components: none.

## Design, accessibility and performance

New styling stays in the central global stylesheet, using shared spacing/surface/status tokens. Tables have captions and scroll regions; risk states retain text and unknown values use neutral styling. Mobile navigation uses the existing dialog-focus hook. Sorting remains available on touch screens and headers expose their state to assistive technology. Reduced-motion support is retained.

Analytics/Recharts and ModelView are dynamically imported. Leaflet remains dynamically imported; event grouping and existing memoized filtering/pagination reduce work. The production route reports approximately 161 kB first-load JavaScript (57.8 kB route), with heavy charts split out.

## Validation

- npm run typecheck: PASS.
- npm run build: PASS (Next.js 15.5.25).
- npm test: 90 passed, zero failed.
- npm run test:e2e: 14 passed, zero failed; no uncaught browser errors in the suite.
- Ten workspace views tested at 320, 375, 768, 1024 and 1440px with no document-level horizontal overflow. Wide comparison/matrix tables intentionally scroll within their own regions.
- E2E also covers event evidence selection/Escape, mobile focus restoration, model success/failure, filter reload, expired auth, public login, notification load failure and retained provider telemetry.
- git diff --check: PASS.
- git diff -- backend: empty. Backend files modified: ZERO.

Browser tests use clearly labeled test-only responses and a nonfunctional fixture token. They do not mutate backend data, approve browser push permission, issue real FCM tokens or send notifications. They establish frontend integration behavior, not real-provider delivery reliability. Screenshots are generated under ignored frontend/test-results/.

## API compatibility and remaining data boundaries

All existing request paths, payloads, authentication helpers, notification preference behavior and Firebase runtime helpers are preserved. The only newly consumed endpoint is the existing read-only /api/v1/model/metrics. Review data remains read-only because the backend exposes no review-write endpoint. Unsupported timestamps, notes, metrics, provider records and geometries remain unavailable; no data is invented. Organization and area administration stay in the existing Settings screen, rather than introducing unsupported routes. This work does not certify a complete WCAG audit or external-provider uptime.

## Files modified

- frontend/app/globals.css
- frontend/app/page.tsx
- frontend/components/EventTable.tsx
- frontend/components/MapView.tsx
- frontend/components/NotificationSettings.tsx
- frontend/components/ProviderHealthGrid.tsx
- frontend/components/ReviewCenter.tsx
- frontend/components/StatusBadge.tsx
- frontend/package-lock.json
- frontend/package.json
- frontend/tests/experience.test.mjs
- frontend/tests/providers.test.mjs
- frontend/tests/push.test.mjs

## Files created

- frontend/.gitignore
- frontend/components/CommandSummary.tsx
- frontend/components/ModelView.tsx
- frontend/docs/FRONTEND_AUDIT.md
- frontend/lib/mapGrouping.ts
- frontend/lib/reviewCandidates.ts
- frontend/playwright.config.ts
- frontend/tests/e2e/workspace.spec.ts
- frontend/docs/FRONTEND_IMPLEMENTATION.md
