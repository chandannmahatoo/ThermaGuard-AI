# Frontend audit — before implementation

The working tree was clean at the start. Backend is frozen.

- Routes: `/` contains landing, login, signup and nine protected in-page workspace views. `/firebase-messaging-config.js` supplies public worker configuration. Root layout imports central CSS and Leaflet CSS.
- Existing components cover KPIs, operational activity, map, filters, paginated events, evidence drawer, provider health, analytics, read-only review readiness, alerts, notification/admin forms, and Copilot.
- API helpers centralize same-origin requests, sessionStorage authentication, HTTP/network errors and timeouts. Firebase registration requires saved preferences. Preserve these contracts.
- Design: global CSS contains tokens and reusable cards/states, but accumulated responsive overrides and dense inline JSX make hierarchy harder to maintain. Sidebar lacks logical groups and mobile modal focus management.
- Events: mobile cards already exist through CSS (the initial summary understated this); sorting is hidden on mobile, headers lack aria-sort, persistence/source/alert state are incomplete. Pagination exists.
- Map: dynamically loaded, selected marker and supporting overlays exist. No fit-results action or visual aggregation; classes appear only in tooltips. Do not invent facility geometries.
- Model: existing `/model/metrics` is not consumed by a dedicated model view. Review export is read-only; no write API exists.
- Providers: eleven existing cards have last-success/error telemetry; a comparison table is missing. Missing telemetry must not imply health.
- Accessibility: existing dialogs trap focus, but mobile navigation does not. Risk unknown currently inherits Normal styling. Loading/error components and reduced-motion support exist.
- Performance: Leaflet is dynamic; Recharts is eagerly imported through Analytics. Event pagination and memoized filters already exist.
- Tests: Node tests exist, but no `test:e2e` script or browser test harness is configured.

Implementation will reuse these screens, centralize additional design rules, add a read-only model view, improve keyboard/mobile operation and add deterministic browser integration coverage. No fake reviews, notification delivery, telemetry, or auth shortcuts in runtime code.
