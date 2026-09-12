'use client';
import React from 'react';
import {
  Flame,
  Activity,
  Radio,
  MapPin,
  CloudSun,
  Wind,
  Globe,
  Route,
  Sparkles,
  Mail,
  BellRing,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
} from 'lucide-react';
import type { ProviderStatusResponse, ProviderHealthEntry } from '../lib/api';
import { ProviderBadge, StatusBadge, type SystemReadinessState } from './StatusBadge';

type ProviderHealthGridProps = {
  providerHealth: ProviderStatusResponse | null;
  isAdmin: boolean;
  demo: boolean;
  syncBusy: boolean;
  onSyncFirms: () => void;
};

const PROVIDER_METADATA: {
  key: string;
  name: string;
  serviceType: string;
  icon: React.ElementType;
  description: string;
}[] = [
  {
    key: 'firms',
    name: 'NASA FIRMS',
    serviceType: 'Thermal Satellite Ingestion',
    icon: Flame,
    description: 'Near-real-time active fire & hotspot observations from VIIRS and MODIS satellites.',
  },
  {
    key: 'osm',
    name: 'OSM / Overpass',
    serviceType: 'Industrial Infrastructure Context',
    icon: Activity,
    description: 'Proximity detection to industrial complexes, quarries, pipelines, and settlements.',
  },
  {
    key: 'copernicus',
    name: 'Copernicus / Sentinel',
    serviceType: 'Multispectral Surface Reflectance',
    icon: Radio,
    description: 'Sentinel-2 L2A normalized difference vegetation index (NDVI) & land cover context.',
  },
  {
    key: 'location',
    name: 'Geocoding (Nominatim)',
    serviceType: 'Geographic Reverse Geocoding',
    icon: MapPin,
    description: 'Resolves raw GPS coordinates into human-readable town, district, and state names.',
  },
  {
    key: 'weather',
    name: 'Weather (Open-Meteo)',
    serviceType: 'Modelled Grid Atmospheric Data',
    icon: CloudSun,
    description: 'Temperature, humidity, precipitation, and wind vectors for event timestamp.',
  },
  {
    key: 'air_quality',
    name: 'Air Quality (Open-Meteo)',
    serviceType: 'Atmospheric Dispersion & Smoke',
    icon: Wind,
    description: 'PM2.5, PM10, CO, NO2, and Ozone atmospheric concentrations at ground level.',
  },
  {
    key: 'eonet',
    name: 'NASA EONET',
    serviceType: 'Natural Earth Hazard Events',
    icon: Globe,
    description: 'Correlates monitored events with official NASA Earth Observatory natural hazard records.',
  },
  {
    key: 'routing',
    name: 'Routing (OpenRouteService)',
    serviceType: 'Emergency Road Logistics',
    icon: Route,
    description: 'Calculates driving paths and response logistics from roads to thermal anomaly.',
  },
  {
    key: 'gemini',
    name: 'Google Gemini AI',
    serviceType: 'Evidence Copilot Explanation',
    icon: Sparkles,
    description: 'Explains verified thermal facts and risk drivers without mutating records.',
  },
  {
    key: 'smtp',
    name: 'SMTP Email Service',
    serviceType: 'Authoritative Notification Dispatch',
    icon: Mail,
    description: 'Dispatches incident alerts to subscribed organizations crossing risk threshold.',
  },
  {
    key: 'firebase',
    name: 'Firebase Cloud Push',
    serviceType: 'Mobile & Browser Push Messaging',
    icon: BellRing,
    description: 'Location-aware push notifications delivered to registered field operator devices.',
  },
];

const fmtTime = (value: string | undefined | null) => {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? null
    : date.toLocaleString('en-IN', {
        timeZone: 'UTC',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }) + ' UTC';
};

const mapStatusToReadiness = (state: string): SystemReadinessState => {
  switch (state) {
    case 'healthy':
    case 'configured':
      return 'REAL';
    case 'disabled':
      return 'UNAVAILABLE';
    case 'blocked':
    case 'not_configured':
    case 'failed':
      return 'BLOCKED';
    case 'degraded':
      return 'FALLBACK';
    default:
      return 'UNAVAILABLE';
  }
};

export default function ProviderHealthGrid({
  providerHealth,
  isAdmin,
  demo,
  syncBusy,
  onSyncFirms,
}: ProviderHealthGridProps) {
  return (
    <div className="providers-view-container">
      {/* Overview header */}
      <div className="providers-view-header">
        <div>
          <h2>External Provider &amp; Model Telemetry</h2>
          <p className="text-muted">
            Live configuration state and the last real interaction recorded in this backend process.
            No keys or credentials are shown, ever. This panel never probes providers synchronously — it reports what has actually happened in this process.
          </p>
        </div>
        {isAdmin && (
          <button
            type="button"
            className="button sync-firms-btn"
            disabled={syncBusy || demo}
            onClick={onSyncFirms}
            title={demo ? 'Disable DEMO_MODE on backend to synchronize real FIRMS feed' : 'Synchronize NASA FIRMS observations'}
          >
            <RefreshCw size={15} className={syncBusy ? 'spin' : ''} />
            {syncBusy ? 'Synchronizing…' : 'Sync NASA FIRMS'}
          </button>
        )}
      </div>

      {demo && (
        <div className="demo-note">
          <b>DEMO ENVIRONMENT ACTIVE</b> · Synthetic telemetry fixtures shown. Provider API keys remain securely guarded on the server.
        </div>
      )}

      {/* Grid of 11 provider cards */}
      <div className="provider-cards-grid">
        {PROVIDER_METADATA.map((meta) => {
          const entry: ProviderHealthEntry | undefined = providerHealth?.providers?.[meta.key];
          const state = (entry?.status || 'unavailable') as string;
          const Icon = meta.icon;
          const readiness = mapStatusToReadiness(state);

          return (
            <article key={meta.key} className={`provider-card card-state-${state}`}>
              <div className="provider-card-top">
                <div className="provider-icon-title">
                  <div className="provider-icon-wrap">
                    <Icon size={18} />
                  </div>
                  <div>
                    <h3 className="provider-card-name">{meta.name}</h3>
                    <span className="provider-service-type">{meta.serviceType}</span>
                  </div>
                </div>
                <div className="provider-badges-col">

                  <ProviderBadge state={state} />
                </div>
              </div>

              <p className="provider-card-desc">{meta.description}</p>

              <div className="provider-telemetry-box">
                {entry ? (
                  <dl className="provider-telemetry-dl">
                    <div>
                      <dt>Enabled / configured</dt><dd>{['healthy', 'configured', 'degraded', 'failed'].includes(state) ? 'Yes / Yes' : state === 'disabled' ? 'No / Unknown' : state === 'not_configured' ? 'Unknown / No' : 'Unknown / Unknown'}</dd></div><div><dt>Interaction</dt><dd>{entry.last_success || entry.last_failure ? 'Recorded in this process' : 'No interaction recorded'}</dd></div><div><dt>Latency</dt>
                      <dd>{entry.last_latency_ms != null ? `${entry.last_latency_ms} ms` : '—'}</dd>
                    </div>
                    <div>
                      <dt>Last Success</dt>
                      <dd>{fmtTime(entry.last_success) || 'No success logged'}</dd>
                    </div>
                    {entry.last_error_category && (
                      <div className="telemetry-error-row">
                        <dt>Last Error</dt>
                        <dd className="text-red">
                          {entry.last_error_category.replace(/_/g, ' ')}
                          {entry.last_failure ? ` (${fmtTime(entry.last_failure)})` : ''}
                        </dd>
                      </div>
                    )}
                  </dl>
                ) : (
                  <p className="provider-no-interaction small">
                    Telemetry unavailable · no interaction recorded
                  </p>
                )}
              </div>
            </article>
          );
        })}
      </div>

      <div className="providers-footer-note"><p>Configured: ready, with no recorded success. Healthy: a live success is recorded. Degraded: the latest interaction failed after a prior success. Failed: no retained success after failure. Blocked: a provider restriction prevents use. Missing telemetry does not establish configuration or health.</p>
        <p className="small">
          Zero ingested observations during FIRMS synchronization is normal when no new detections occur within the satellite query window. Real ingestion is isolated from demo fixtures; provider credentials never touch client browsers.
        </p>
      </div>
    </div>
  );
}
