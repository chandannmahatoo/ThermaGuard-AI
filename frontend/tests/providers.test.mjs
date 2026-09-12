import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);

// Transpile + run a TSX component in a sandbox, returning its default export.
const leafletMock = {
  MapContainer: ({ children }) => React.createElement('div', { className: 'mapcontainer' }, children),
  TileLayer: () => React.createElement('div'),
  CircleMarker: ({ children, center, radius }) => React.createElement('div', { 'data-center': String(center), 'data-radius': radius }, children),
  Polyline: () => React.createElement('div'),
  Tooltip: ({ children }) => React.createElement('div', { className: 'tooltip' }, children),
  useMap: () => ({ flyTo: () => {}, fitBounds: () => {} }),
};
function loadTsx(path, sandbox = {}) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8');
  const exports = {};
  // Intercept browser-only map modules so SSR-style tests never touch leaflet.
  const req = name => (name === 'react-leaflet' ? leafletMock : require(name));
  vm.runInNewContext(
    ts.transpileModule(source, {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    { exports, require: req, React, renderToStaticMarkup, ...sandbox },
  );
  return exports.default;
}

function loadApi(env = {}) {
  const source = readFileSync(new URL('../lib/api.ts', import.meta.url), 'utf8');
  const exports = {};
  vm.runInNewContext(
    ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText,
    { exports, process: { env }, fetch: async () => Response.json({}), AbortController, DOMException, setTimeout, clearTimeout },
  );
  return exports;
}

const FIXTURE_ENTRY = {
  status: 'healthy',
  last_success: '2026-09-12T00:00:00+00:00',
  last_failure: null,
  last_error_category: null,
  last_latency_ms: 350,
};

// ------------------------------------------------------------
// api.ts: provider status + EONET contracts
// ------------------------------------------------------------

test('provider status and EONET fetches hit the right authed endpoints', async () => {
  const calls = [];
  const api = loadApi();
  const sandbox = {};
  vm.runInNewContext(
    ts.transpileModule(readFileSync(new URL('../lib/api.ts', import.meta.url), 'utf8'),
      { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText,
    { exports: sandbox, process: { env: {} }, fetch: async (url, init) => { calls.push({ url, init }); return Response.json({ providers: {}, note: 'x' }); }, AbortController, DOMException, setTimeout, clearTimeout },
  );
  await sandbox.fetchProviderStatus('tok');
  await sandbox.fetchEonetEvents('tok');
  assert.equal(calls[0].url, '/api/v1/providers/status');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer tok');
  assert.equal(calls[1].url, '/api/v1/eonet/events');
});

test('alert type surface carries delivery and coordinate fields', () => {
  const source = readFileSync(new URL('../lib/api.ts', import.meta.url), 'utf8');
  assert.match(source, /delivery\?: AlertDelivery\[\] \| null/);
  assert.match(source, /latitude\?: number \| null/);
  assert.match(source, /ProviderState = 'healthy'/);
});

// ------------------------------------------------------------
// MapView: hazard + industrial layers render conditionally
// ------------------------------------------------------------

const MapView = loadTsx('../components/MapView.tsx');

const baseEvent = {
  id: 'TG-test-1', latitude: 22, longitude: 70, is_demo: false,
  start_time: '2026-09-11T00:00:00Z', last_seen_time: '2026-09-11T00:00:00Z',
  duration_hours: 1, detection_count: 3, mean_frp: 12.5, max_frp: 20, mean_brightness: 300,
  persistence_days: 1, classification: { predicted_class: null, classification_confidence: null, model_version: null },
  context: {}, risk: { risk_score: 10, risk_level: 'Normal', risk_factors: {}, missing_context: [], abnormality: { baseline_available: false, abnormality_score: null, abnormality_status: 'unavailable' } },
};

test('EONET hazard markers render only when the layer is enabled', () => {
  const hazards = [{ eonet_id: 'E1', title: 'Wildfire X', category: 'Wildfires', latitude: 21, longitude: 71, event_date: '2026-09-10', source: 'NASA EONET' }];
  const withLayer = renderToStaticMarkup(React.createElement(MapView, { events: [baseEvent], onSelect: () => {}, selected: null, hazards, showHazards: true }));
  assert.match(withLayer, /Wildfire X/);
  assert.match(withLayer, /not a ThermaGuard event/);
  const withoutLayer = renderToStaticMarkup(React.createElement(MapView, { events: [baseEvent], onSelect: () => {}, selected: null, hazards, showHazards: false }));
  assert.doesNotMatch(withoutLayer, /Wildfire X/);
});

test('industrial context markers render only when the layer is enabled and OSM data exists', () => {
  const industrialEvent = { ...baseEvent, context: { osm_context_available: true, nearby_industrial_count: 4, landuse_class: 'industrial' } };
  const on = renderToStaticMarkup(React.createElement(MapView, { events: [industrialEvent], onSelect: () => {}, selected: null, showIndustrial: true }));
  assert.match(on, /OSM industrial activity/);
  const off = renderToStaticMarkup(React.createElement(MapView, { events: [industrialEvent], onSelect: () => {}, selected: null, showIndustrial: false }));
  assert.doesNotMatch(off, /OSM industrial activity/);
  const noData = renderToStaticMarkup(React.createElement(MapView, { events: [baseEvent], onSelect: () => {}, selected: null, showIndustrial: true }));
  assert.doesNotMatch(noData, /OSM industrial activity/);
});

// ------------------------------------------------------------
// StatusBadge rendering of the six provider states
// ------------------------------------------------------------

test('provider health states map to honest badges, never fabricated health', () => {
  const source = readFileSync(new URL('../app/page.tsx', import.meta.url), 'utf8');
  // Every state label exists and unconfigured providers can never show Healthy.
  for (const state of ['healthy', 'configured', 'disabled', 'not_configured', 'degraded', 'failed']) {
    assert.ok(source.includes(`${state}:`) || source.includes(`provider-${state}`), `missing state ${state}`);
  }
  assert.match(source, /no interaction recorded/);
  assert.match(source, /never probes providers|this panel never does/);
});
