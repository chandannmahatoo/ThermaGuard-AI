import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
import ts from 'typescript';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const require = createRequire(import.meta.url);

const leafletMock = {
  MapContainer: ({ children }) => React.createElement('div', { className: 'mapcontainer' }, children),
  TileLayer: () => React.createElement('div'),
  CircleMarker: ({ children, center, radius }) =>
    React.createElement('div', { 'data-center': String(center), 'data-radius': radius }, children),
  Polyline: () => React.createElement('div', { className: 'polyline' }),
  Tooltip: ({ children }) => React.createElement('div', { className: 'tooltip' }, children),
  useMap: () => ({ flyTo: () => {}, fitBounds: () => {} }),
};

function loadTsx(path, sandbox = {}) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8');
  const exports = {};
  const req = (name) => {
    if (name === 'react-leaflet') return leafletMock;
    if (name === './StatusBadge' || name === '../components/StatusBadge') {
      return loadTsx('../components/StatusBadge.tsx', sandbox);
    }
    return require(name);
  };
  vm.runInNewContext(
    ts.transpileModule(source, {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        jsx: ts.JsxEmit.ReactJSX,
        esModuleInterop: true,
        target: ts.ScriptTarget.ES2022,
      },
    }).outputText,
    { exports, require: req, React, renderToStaticMarkup, ...sandbox }
  );
  return exports;
}

const mockEvent = {
  id: 'TG-test-event-12345',
  latitude: 21.15,
  longitude: 79.08,
  is_demo: false,
  start_time: '2026-09-11T12:00:00Z',
  last_seen_time: '2026-09-11T14:30:00Z',
  duration_hours: 2.5,
  detection_count: 5,
  mean_frp: 45.2,
  max_frp: 88.0,
  mean_brightness: 345.2,
  persistence_days: 2,
  classification: {
    predicted_class: 'industrial_flare',
    classification_confidence: 0.89,
    model_version: 'rf-mvp-v1',
  },
  context: {
    osm_context_available: true,
    nearby_industrial_count: 3,
    landuse_class: 'industrial',
    satellite_context_available: true,
    ndvi: 0.245,
    acquisition_date: '2026-09-10',
    provider: 'Sentinel-2 L2A',
    weather: {
      status: 'available',
      provider: 'open_meteo',
      temperature_c: 32.5,
      relative_humidity_percent: 45,
      wind_speed_kmh: 12.4,
    },
    location: {
      status: 'available',
      provider: 'nominatim',
      display_name: 'Nagpur Industrial Zone, Maharashtra',
    },
    routing: {
      status: 'available',
      distance_m: 4500,
      duration_seconds: 480,
      geometry: { type: 'LineString', coordinates: [[79.08, 21.15], [79.10, 21.18]] },
    },
  },
  risk: {
    risk_score: 86,
    risk_level: 'Critical',
    risk_factors: { thermal_intensity: 35, persistence: 25, industrial_proximity: 26 },
    missing_context: [],
    abnormality: {
      baseline_available: true,
      abnormality_score: 2.8,
      abnormality_status: 'significantly_elevated',
    },
  },
  sensor_summary: {
    cross_sensor_confirmed: true,
    unique_satellite_count: 2,
  },
  source_counts: {
    viirs_snpp: 3,
    modis_aqua: 2,
  },
};

// 1. Overview KPIs Component Test
test('OverviewKPIs renders real values, context coverage, and cross-sensor counts', () => {
  const mod = loadTsx('../components/OverviewKPIs.tsx');
  const Component = mod.default;
  const html = renderToStaticMarkup(
    React.createElement(Component, {
      events: [mockEvent],
      alerts: [{ id: 1, event_id: mockEvent.id, risk_level: 'Critical', status: 'open', created_at: '2026-09-11', is_demo: false, notification_status: 'sent' }],
      model: { training_ready: true, model_available: true, model_version: 'v1.0', eligible_labeled_rows: 32, reason: '', feature_version: 'f1' },
      providerHealth: { providers: { firms: { status: 'healthy', last_latency_ms: 220, last_success: '2026-09-11', last_failure: null, last_error_category: null } }, note: '' },
      busy: false,
      demo: false,
    })
  );
  assert.match(html, /Active Monitored Events/);
  assert.match(html, />01</);
  assert.match(html, /Critical Events/);
  assert.match(html, /Mean Radiative Power/);
  assert.match(html, /45\.2/);
  assert.match(html, /Cross-Sensor Events/);
  assert.match(html, /Context Coverage/);
  assert.match(html, /100%/);
});

// 2. StatusBadge & ProviderBadge
test('StatusBadge and ProviderBadge render all required states honestly', () => {
  const mod = loadTsx('../components/StatusBadge.tsx');
  const { StatusBadge, ProviderBadge, RiskBadge } = mod;

  const states = ['healthy', 'configured', 'disabled', 'not_configured', 'degraded', 'failed'];
  for (const s of states) {
    const html = renderToStaticMarkup(React.createElement(ProviderBadge, { state: s }));
    assert.match(html, new RegExp(`provider-${s}`));
  }

  const criticalBadge = renderToStaticMarkup(React.createElement(RiskBadge, { level: 'Critical' }));
  assert.match(criticalBadge, /badge critical/);
  assert.match(criticalBadge, /Critical/);

  const realBadge = renderToStaticMarkup(React.createElement(StatusBadge, { state: 'REAL' }));
  assert.match(realBadge, /status-badge real/);
});

// 3. ProviderHealthGrid
test('ProviderHealthGrid renders 11 provider cards with latency and last success', () => {
  const mod = loadTsx('../components/ProviderHealthGrid.tsx');
  const Component = mod.default;
  const html = renderToStaticMarkup(
    React.createElement(Component, {
      providerHealth: {
        providers: {
          firms: { status: 'healthy', last_latency_ms: 145, last_success: '2026-09-12T00:00:00Z', last_failure: null, last_error_category: null },
          gemini: { status: 'healthy', last_latency_ms: 420, last_success: '2026-09-12T00:00:00Z', last_failure: null, last_error_category: null },
          smtp: { status: 'configured', last_latency_ms: null, last_success: null, last_failure: null, last_error_category: null },
        },
        note: 'test note',
      },
      isAdmin: true,
      demo: false,
      syncBusy: false,
      onSyncFirms: () => {},
    })
  );

  assert.match(html, /NASA FIRMS/);
  assert.match(html, /Google Gemini AI/);
  assert.match(html, /SMTP Email Service/);
  assert.match(html, /145 ms/);
  assert.match(html, /Sync NASA FIRMS/);
  assert.match(html, /no interaction recorded/);
});

// 4. AlertCenter with delivery chips & acknowledge
test('AlertCenter renders incident cards with delivery audit chips and acknowledge button', () => {
  const mod = loadTsx('../components/AlertCenter.tsx');
  const Component = mod.default;
  const alerts = [
    {
      id: 101,
      event_id: 'TG-alert-event-1',
      organization_id: 1,
      risk_level: 'Critical',
      created_at: '2026-09-12T08:00:00Z',
      status: 'open',
      notification_status: 'dispatched',
      latitude: 19.5,
      longitude: 75.2,
      delivery: [
        { channel: 'email', status: 'sent', sent_at: '2026-09-12T08:01:00Z' },
        { channel: 'push', status: 'sent', sent_at: '2026-09-12T08:01:00Z' },
      ],
      is_demo: false,
    },
  ];

  const html = renderToStaticMarkup(
    React.createElement(Component, {
      alerts,
      onAcknowledge: () => {},
      ackBusy: null,
      onSelectEvent: () => {},
      busy: false,
    })
  );

  assert.match(html, /Critical Risk Notification/);
  assert.match(html, /TG-alert-event-1/);
  assert.match(html, /Email: sent/);
  assert.match(html, /Push: sent/);
  assert.match(html, /Acknowledge/);
});

// 5. EventTable with sorting, pagination, and context completeness dots
test('EventTable renders sortable headers and context completeness dots', () => {
  const mod = loadTsx('../components/EventTable.tsx');
  const Component = mod.default;
  const html = renderToStaticMarkup(
    React.createElement(Component, {
      events: [mockEvent],
      selectedId: null,
      onSelect: () => {},
      busy: false,
    })
  );

  assert.match(html, /Event ID/);
  assert.match(html, /ML Classification/);
  assert.match(html, /Mean FRP/);
  assert.match(html, /Context Coverage/);
  assert.match(html, /industrial flare/);
  assert.match(html, /45\.2/);
  assert.match(html, /dot-active/);
});

// 6. CopilotModal with Gemini vs Fallback badge
test('CopilotModal displays Gemini badge, fallback notice, and prompt suggestions', () => {
  const mod = loadTsx('../components/CopilotModal.tsx');
  const Component = mod.default;

  const geminiHtml = renderToStaticMarkup(
    React.createElement(Component, {
      isOpen: true,
      onClose: () => {},
      selected: mockEvent,
      question: '',
      setQuestion: () => {},
      answer: 'This event exhibits intense localized fire radiative power.',
      chatMode: 'gemini',
      chatBusy: false,
      onAsk: () => {},
      onSelectSuggestedQuestion: () => {},
    })
  );
  assert.match(geminiHtml, /Powered by Gemini API/);
  assert.match(geminiHtml, /intense localized fire radiative power/);
  assert.match(geminiHtml, /Evidence Grounded/);

  const fallbackHtml = renderToStaticMarkup(
    React.createElement(Component, {
      isOpen: true,
      onClose: () => {},
      selected: mockEvent,
      question: '',
      setQuestion: () => {},
      answer: 'Stored evidence summary.',
      chatMode: 'deterministic_fallback',
      chatBusy: false,
      onAsk: () => {},
      onSelectSuggestedQuestion: () => {},
    })
  );
  assert.match(fallbackHtml, /Deterministic Fallback/);
  assert.match(fallbackHtml, /Gemini unavailable — deterministic evidence summary/);
});

// 7. NotificationSettings Component
test('NotificationSettings renders alert radius slider, coordinates inputs, and admin controls', () => {
  const mod = loadTsx('../components/NotificationSettings.tsx');
  const Component = mod.default;
  const html = renderToStaticMarkup(
    React.createElement(Component, {
      notif: {
        notifications_enabled: true,
        latitude: 21.1458,
        longitude: 79.0882,
        alert_radius_km: 25,
      },
      notifBusy: false,
      onSaveNotif: () => {},
      isAdmin: true,
      organizations: [{ id: 1, name: 'Maharashtra Fire Service', email: 'fire@mh.gov.in' }],
      assignments: [{ id: 1, organization_id: 1, area_name: 'Nagpur', bounds: [78, 20, 80, 22] }],
      onCreateOrg: async () => {},
      onAssignArea: async () => {},
      onUpdateThreshold: async () => {},
      onAssignUser: async () => {},
    })
  );

  assert.match(html, /Incident Notification Preferences/);
  assert.match(html, /Alert Radius \(25 km\)/);
  assert.match(html, /21\.1458/);
  assert.match(html, /79\.0882/);
  assert.match(html, /Maharashtra Fire Service/);
  assert.match(html, /Nagpur/);
  assert.match(html, /Save Notification Preferences/);
});

// 8. ReviewCenter Component
test('ReviewCenter tracks eligible rows progress towards the 30-row gate', () => {
  const mod = loadTsx('../components/ReviewCenter.tsx');
  const Component = mod.default;
  const html = renderToStaticMarkup(
    React.createElement(Component, {
      model: {
        training_ready: true,
        model_available: true,
        model_version: 'rf-2026-v2',
        eligible_labeled_rows: 32,
        reason: '',
        feature_version: 'v1.4',
      },
      isAdmin: true,
      trainBusy: false,
      onTrainModel: () => {},
    })
  );

  assert.match(html, /RandomForest Classifier/);
  assert.match(html, /rf-2026-v2/);
  assert.match(html, /32<\/b> \/ 30/);
  assert.match(html, /100%/);
  assert.match(html, /RandomForest is Source-of-Truth/);
  assert.match(html, /Train Reviewed Dataset/);
});
