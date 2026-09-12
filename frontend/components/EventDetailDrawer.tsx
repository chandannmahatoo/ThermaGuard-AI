'use client';
import React, { useState, useEffect } from 'react';
import {
  X,
  Flame,
  Shield,
  Layers,
  Sparkles,
  MapPin,
  Clock,
  Activity,
  Compass,
  FileJson,
  Navigation,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
} from 'lucide-react';
import type { ThermalEvent, Evidence, ProviderContext, EventContext } from '../lib/api';
import {useDialogFocus} from '../lib/useDialogFocus';
import ContextCoverage from './ContextCoverage';
import ContextPanel from './ContextPanel';
import { RiskBadge } from './StatusBadge';

type EventDetailDrawerProps = {
  event: ThermalEvent;
  onClose: () => void;
  onZoom?: () => void;
  token: string;
  evidence: Evidence | null;
  evidenceBusy: boolean;
  history: ThermalEvent[];
  onOpenCopilot: () => void;
  onUpdateEventContext: (updatedContext: EventContext) => void;
};

const num = (value: unknown, digits = 1, fallback = 'Unavailable') =>
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : fallback;

const fmtTime = (value: string | undefined | null) => {
  if (!value) return 'Unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Unavailable'
    : date.toLocaleString('en-IN', {
        timeZone: 'UTC',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }) + ' UTC';
};

export default function EventDetailDrawer({
  event,
  onClose,
  onZoom,
  token,
  evidence,
  evidenceBusy,
  history,
  onOpenCopilot,
  onUpdateEventContext,
}: EventDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [copied, setCopied] = useState(false);

  const dialogRef = useDialogFocus<HTMLElement>();

  function copyId() {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(event.id).then(()=>setCopied(true)).catch(()=>setCopied(false));
      setTimeout(() => setCopied(false), 2000);
    }
  }

  const isCrossSensor = event.sensor_summary?.cross_sensor_confirmed === true;
  const isDemo = event.is_demo;

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside ref={dialogRef}
        className="drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Event intelligence detail"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="drawer-head">
          <div className="drawer-title-group">
            <span className="eyebrow">EVENT INTELLIGENCE DOSSIER</span>
            <div className="drawer-id-row">
              <h2 className="drawer-id-title">{event.id}</h2>
              <button
                type="button"
                className="drawer-copy-button"
                onClick={copyId}
                title="Copy event identifier"
                aria-label="Copy event ID"
              >
                {copied ? <Check size={14} className="text-green" /> : <Copy size={14} />}
              </button>
            </div>
          </div>
          <button
            autoFocus
            className="drawer-close-button"
            aria-label="Close event intelligence drawer"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>

        {/* Demo Alert if applicable */}
        {isDemo && (
          <div className="demo-note">
            <b>DEMO RECORD</b> · Deterministic benchmark event. Not an unverified live incident.
          </div>
        )}

        {/* Risk Hero Banner */}
        <div className="risk-hero-card">
          <div className="risk-hero-left">
            <span className="risk-hero-label">AUTHORITATIVE RISK SCORE</span>
            <div className="risk-hero-score-row">
              <strong className="risk-hero-score">
                {num(event.risk?.risk_score, 0, '—')}
              </strong>
              <span className="risk-hero-max">/ 100</span>
            </div>
            <span className="risk-hero-sub">Deterministic calculation</span>
          </div>
          <div className="risk-hero-right">
            <RiskBadge level={event.risk?.risk_level} />
            <div className="risk-hero-ml-class">
              <span className="text-muted">ML Class:</span>{' '}
              <b>
                {event.classification?.predicted_class
                  ? event.classification.predicted_class.replace(/_/g, ' ')
                  : 'Unclassified'}
              </b>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="drawer-tabs" aria-label="Event detail sections">
          {Object.entries({overview:'Overview',thermal:'Thermal Evidence',location:'Location',weather:'Weather',air_quality:'Air Quality',satellite:'Satellite',industrial:'Industrial Context',eonet:'Natural Hazards',routing:'Routing',copilot:'AI Copilot',raw:'Raw Evidence'}).map(([id,title])=><button type="button" key={id} className={`drawer-tab ${activeTab===id?'active':''}`} aria-pressed={activeTab===id} onClick={()=>setActiveTab(id)}>{title}</button>)}
        </nav>
        {['location','weather','air_quality','eonet'].includes(activeTab) && <div className="drawer-tab-content"><ContextPanel
          section={activeTab}
          event={event}
          token={token}
          onContext={onUpdateEventContext}
          onRoute={(packet: ProviderContext) => onUpdateEventContext({ ...event.context, routing: packet })}
        />{activeTab==='location' && <button className="button" onClick={async()=>{try{await navigator.clipboard.writeText(`${event.latitude}, ${event.longitude}`);setCopied(true)}catch{setCopied(false)}}}>{copied?'Copied':'Copy coordinates'}</button>}</div>}
        {activeTab==='satellite' && <div className="drawer-tab-content"><h3>Satellite context</h3><p>{event.context.satellite_context_available ? 'Available' : event.context.reason || 'Not available'}</p>{event.context.satellite_context_available && <dl>{['ndvi','acquisition_date','provider','satellite_image_reference','land_cover'].map(key=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{String(event.context[key]??'Not available')}</dd></div>)}</dl>}</div>}
        {activeTab==='industrial' && <div className="drawer-tab-content"><h3>OSM industrial context</h3><p>{event.context.osm_context_available ? 'Available' : event.context.osm_reason || 'Not available'}</p>{event.context.osm_context_available && <dl>{['nearby_industrial_count','nearby_facility_count','nearby_facility_names','distance_to_industrial_m','distance_to_residential_m','landuse_class'].map(key=><div key={key}><dt>{key.replaceAll('_',' ')}</dt><dd>{String(event.context[key]??'Not available')}</dd></div>)}</dl>}</div>}

        {/* Tab 1: Overview */}
        {activeTab === 'overview' && (
          <div className="drawer-tab-content">
            <ContextCoverage context={event.context}/><h3 className="drawer-section-title">Classification &amp; Location</h3>
            <dl className="drawer-facts-grid">
              <div>
                <dt>Predicted Class</dt>
                <dd>
                  {event.classification?.predicted_class
                    ? event.classification.predicted_class.replace(/_/g, ' ')
                    : 'Unclassified (decision support)'}
                </dd>
              </div>
              <div>
                <dt>Model Confidence</dt>
                <dd>
                  {typeof event.classification?.classification_confidence === 'number'
                    ? (event.classification.classification_confidence * 100).toFixed(1) + '%'
                    : 'Not available'}
                </dd>
              </div>
              <div>
                <dt>Model Version</dt>
                <dd>{event.classification?.model_version || 'Not available'}</dd>
              </div>
              <div>
                <dt>Location</dt>
                <dd>
                  {event.context?.location?.status === 'available' && event.context.location.display_name
                    ? event.context.location.display_name
                    : `${num(event.latitude, 4, '?')}° N, ${num(event.longitude, 4, '?')}° E`}
                </dd>
              </div>
              <div>
                <dt>First Detected</dt>
                <dd>{fmtTime(event.start_time)}</dd>
              </div>
              <div>
                <dt>Latest Observation</dt>
                <dd>{fmtTime(event.last_seen_time)}</dd>
              </div>
              <div>
                <dt>Active Duration</dt>
                <dd>{num(event.duration_hours, 1)} hours</dd>
              </div>
              <div>
                <dt>Observations</dt>
                <dd>{event.detection_count ?? '—'} hotspots</dd>
              </div>
            </dl>

            <h3 className="drawer-section-title">Deterministic Risk Factors</h3>
            <div className="drawer-factors-list">
              {Object.entries(event.risk?.risk_factors || {}).map(([factor, value]) => (
                <div className="factor-row" key={factor}>
                  <div className="factor-row-header">
                    <span className="factor-name">{factor.replace(/_/g, ' ')}</span>
                    <b className="factor-score">+{num(value, 0)}</b>
                  </div>
                  <progress
                    className="factor-progress"
                    max="100"
                    value={typeof value === 'number' ? Math.min(100, Math.max(0, value)) : 0}
                  />
                </div>
              ))}
            </div>

            <div className="drawer-baseline-box">
              <h4>Historical Baseline &amp; Anomaly</h4>
              <p>
                {event.risk?.abnormality?.baseline_available
                  ? `Status: ${event.risk.abnormality.abnormality_status.replace(/_/g, ' ')}${
                      typeof event.risk.abnormality.abnormality_score === 'number'
                        ? ` (deviation: ${event.risk.abnormality.abnormality_score})`
                        : ''
                    }`
                  : 'Historical baseline is currently unavailable for this grid cell.'}
              </p>
              <p className="small">
                {history.length > 0
                  ? `${history.length} earlier recorded event${history.length === 1 ? '' : 's'} in vicinity.`
                  : 'No earlier recorded thermal events in this local area.'}
              </p>
            </div>
          </div>
        )}

        {/* Tab 2: Thermal Evidence */}
        {activeTab === 'thermal' && (
          <div className="drawer-tab-content">
            <h3 className="drawer-section-title">Radiative &amp; Sensor Measurements</h3>
            <dl className="drawer-facts-grid">
              <div>
                <dt>Mean Fire Radiative Power</dt>
                <dd>{num(event.mean_frp, 1)} MW</dd>
              </div>
              <div>
                <dt>Maximum FRP</dt>
                <dd>{num(event.max_frp, 1)} MW</dd>
              </div>
              <div>
                <dt>Mean Brightness Temperature</dt>
                <dd>{num(event.mean_brightness, 1)} K</dd>
              </div>
              <div>
                <dt>Persistence</dt>
                <dd>
                  {event.persistence_days != null
                    ? `${event.persistence_days} day${event.persistence_days === 1 ? '' : 's'}`
                    : 'Unavailable'}
                </dd>
              </div>
              <div>
                <dt>Spatial Spread</dt>
                <dd>{typeof event.spatial_spread_km === 'number' ? `${event.spatial_spread_km.toFixed(2)} km` : 'Point anomaly'}</dd>
              </div>
              <div>
                <dt>Nighttime Fraction</dt>
                <dd>{typeof event.night_fraction === 'number' ? `${(event.night_fraction * 100).toFixed(0)}%` : 'Unavailable'}</dd>
              </div>
            </dl>

            <h3 className="drawer-section-title">Satellite Sensor Breakdown</h3>
            {event.source_counts && (
              <dl className="drawer-facts-grid">
                {Object.entries(event.source_counts).map(([source, count]) => (
                  <div key={source}>
                    <dt>{source === 'legacy_unknown' ? 'Legacy source' : source.replace(/_/g, ' ')}</dt>
                    <dd>{count} observations</dd>
                  </div>
                ))}
              </dl>
            )}

            <div className="drawer-sensor-confirmation">
              <div className="sensor-confirmation-icon">
                {isCrossSensor ? <CheckCircle2 size={18} className="text-green" /> : <AlertCircle size={18} className="text-amber" />}
              </div>
              <div>
                <b>{isCrossSensor ? 'Cross-Sensor Confirmed' : 'Single-Sensor Observation'}</b>
                <p className="small">
                  {isCrossSensor
                    ? 'Thermal signature observed across both VIIRS and MODIS instruments, reducing false-positive likelihood.'
                    : 'Observation detected by a single sensor pass. Requires contextual verification.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: External Context */}
        {activeTab === 'context' && (
          <div className="drawer-tab-content">
            <ContextPanel
              key={event.id}
              event={event}
              token={token}
              onContext={onUpdateEventContext}
              onRoute={(packet: ProviderContext) => {
                onUpdateEventContext({ ...event.context, routing: packet });
              }}
            />

            <div className="context-satellite-summary">
              <h4>Copernicus Sentinel-2 Surface Context</h4>
              <p>
                {event.context?.satellite_context_available
                  ? `NDVI: ${typeof event.context.ndvi === 'number' ? event.context.ndvi.toFixed(3) : 'Unavailable'} · Acquisition: ${event.context.acquisition_date || 'Date unavailable'} · Source: ${event.context.provider || 'Sentinel-2 L2A'}`
                  : `Satellite context: ${String(event.context?.reason || 'Not configured').replace(/_/g, ' ')}`}
              </p>
            </div>
          </div>
        )}

        {/* Tab 4: Road Routing */}
        {activeTab === 'routing' && (
          <div className="drawer-tab-content">
            <div className="routing-standalone-card">
              <h4>OpenRouteService Response Access</h4>
              <p className="small">
                Calculate driving distance and road access route from the thermal anomaly location to emergency response stations or staging areas.
              </p>
              <ContextPanel
                section="routing"
                key={`routing-${event.id}`}
                event={event}
                token={token}
                onContext={onUpdateEventContext}
                onRoute={(packet: ProviderContext) => {
                  onUpdateEventContext({ ...event.context, routing: packet });
                }}
              />
            </div>
          </div>
        )}

        {/* Tab 5: AI Copilot */}
        {activeTab === 'copilot' && (
          <div className="drawer-tab-content">
            <div className="drawer-copilot-shortcut-card">
              <div className="copilot-card-badge">
                <Sparkles size={16} />
                <span>ThermaGuard AI Copilot</span>
              </div>
              <h4>Explain this thermal event</h4>
              <p className="small">
                Generate an evidence-grounded operational explanation powered by Gemini (or deterministic fallback if offline).
                The Copilot explains verified observations and never overrides ML classification or authoritative risk scores.
              </p>
              <button
                type="button"
                className="primary drawer-copilot-btn"
                onClick={onOpenCopilot}
              >
                <Sparkles size={15} />
                Launch Copilot Explanation
              </button>
            </div>
          </div>
        )}

        {/* Tab 6: Raw JSON */}
        {activeTab === 'raw' && (
          <div className="drawer-tab-content">
            <h3 className="drawer-section-title">Verified Raw Payload</h3>
            <pre className="drawer-json-viewer">
              {evidenceBusy
                ? 'Retrieving verified evidence packet from database…'
                : evidence
                ? JSON.stringify(
                    {
                      event: evidence.event,
                      detected_facts: evidence.detected_facts,
                      model_interpretation: evidence.model_interpretation,
                      risk_assessment: evidence.risk_assessment,
                    },
                    null,
                    2
                  )
                : JSON.stringify(event, null, 2)}
            </pre>
          </div>
        )}

        {/* Drawer Bottom Actions */}
        <div className="drawer-bottom-actions">{onZoom && <button className="button" onClick={onZoom}>View on map</button>}
          <button
            type="button"
            className="primary drawer-explain-button"
            onClick={onOpenCopilot}
          >
            <Sparkles size={16} />
            Explain Event with Copilot
          </button>
        </div>
      </aside>
    </div>
  );
}
