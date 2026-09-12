'use client';
import React from 'react';
import {
  Flame,
  AlertTriangle,
  ScanLine,
  Layers,
  Activity,
  Bell,
  ShieldCheck,
  Radio,
} from 'lucide-react';
import type { ThermalEvent, Alert, ModelStatus, ProviderStatusResponse } from '../lib/api';

type OverviewKPIsProps = {
  events: ThermalEvent[];
  alerts: Alert[];
  model: ModelStatus | null;
  providerHealth: ProviderStatusResponse | null;
  busy: boolean;
  demo: boolean;
};

export default function OverviewKPIs({
  events,
  alerts,
  model,
  providerHealth,
  busy,
  demo,
}: OverviewKPIsProps) {
  // Real calculations only - never invented
  const totalEvents = events.length;
  const criticalCount = events.filter((e) => e.risk?.risk_level === 'Critical').length;
  const totalDetections = events.reduce((sum, e) => sum + (e.detection_count || 0), 0);
  const crossSensorCount = events.filter(
    (e) => e.sensor_summary?.cross_sensor_confirmed === true
  ).length;

  // Context coverage: events with either OSM or satellite or weather context
  const enrichedCount = events.filter(
    (e) =>
      e.context?.osm_context_available ||
      e.context?.satellite_context_available ||
      e.context?.weather?.status === 'available'
  ).length;
  const contextCoveragePct = totalEvents > 0 ? Math.round((enrichedCount / totalEvents) * 100) : null;

  // Provider health calculation
  const providersList = providerHealth?.providers ? Object.values(providerHealth.providers) : [];
  const healthyProvidersCount = providersList.filter((p) => p.status === 'healthy').length;
  const totalProvidersCount = providersList.length || 11;

  const openAlertsCount = alerts.filter((a) => a.status === 'open').length;

  const meanFrp = totalEvents > 0
    ? events.reduce((sum, e) => sum + (typeof e.mean_frp === 'number' ? e.mean_frp : 0), 0) / totalEvents
    : 0;

  return (
    <div className="stats-kpi-grid">
      {/* 1. Monitored Events */}
      <article className="stat-card">
        <div className="stat-card-header">
          <span className="stat-card-title">Active Monitored Events</span>
          <span className="stat-icon stat-icon-cyan">
            <ScanLine size={16} />
          </span>
        </div>
        {busy && totalEvents === 0 ? (
          <div className="skeleton-bar" />
        ) : (
          <strong className="stat-card-value">
            {String(totalEvents).padStart(2, '0')}
          </strong>
        )}
        <p className="stat-card-detail">
          {totalDetections} satellite detections{demo ? ' · Demo mode' : ' · Near-real-time'}
        </p>
      </article>

      {/* 2. Critical Events */}
      <article className="stat-card stat-card-critical">
        <div className="stat-card-header">
          <span className="stat-card-title">Critical Events</span>
          <span className="stat-icon stat-icon-red">
            <Flame size={16} />
          </span>
        </div>
        {busy && totalEvents === 0 ? (
          <div className="skeleton-bar" />
        ) : (
          <strong className="stat-card-value text-red">
            {String(criticalCount).padStart(2, '0')}
          </strong>
        )}
        <p className="stat-card-detail">
          Deterministic risk score &gt; 80
        </p>
      </article>

      {/* 3. Mean Fire Radiative Power */}
      <article className="stat-card">
        <div className="stat-card-header">
          <span className="stat-card-title">Mean Radiative Power</span>
          <span className="stat-icon stat-icon-amber">
            <Activity size={16} />
          </span>
        </div>
        {busy && totalEvents === 0 ? (
          <div className="skeleton-bar" />
        ) : (
          <strong className="stat-card-value">
            {meanFrp ? meanFrp.toFixed(1) : '0.0'}
            <small className="stat-unit">MW</small>
          </strong>
        )}
        <p className="stat-card-detail">
          Average intensity across events
        </p>
      </article>

      {/* 4. Cross-Sensor Confirmed */}
      <article className="stat-card">
        <div className="stat-card-header">
          <span className="stat-card-title">Cross-Sensor Events</span>
          <span className="stat-icon stat-icon-blue">
            <Layers size={16} />
          </span>
        </div>
        {busy && totalEvents === 0 ? (
          <div className="skeleton-bar" />
        ) : (
          <strong className="stat-card-value">
            {String(crossSensorCount).padStart(2, '0')}
          </strong>
        )}
        <p className="stat-card-detail">
          Multi-satellite agreement (MODIS &amp; VIIRS)
        </p>
      </article>

      {/* 5. Context Coverage */}
      <article className="stat-card">
        <div className="stat-card-header">
          <span className="stat-card-title">Context Coverage</span>
          <span className="stat-icon stat-icon-teal">
            <Radio size={16} />
          </span>
        </div>
        {busy && totalEvents === 0 ? (
          <div className="skeleton-bar" />
        ) : (
          <strong className="stat-card-value">
            {contextCoveragePct !== null ? `${contextCoveragePct}%` : 'Unavailable'}
          </strong>
        )}
        <p className="stat-card-detail">
          {enrichedCount} of {totalEvents} events enriched with external context
        </p>
      </article>

      {/* 6. Providers Healthy */}
      <article className="stat-card">
        <div className="stat-card-header">
          <span className="stat-card-title">Providers Healthy</span>
          <span className="stat-icon stat-icon-green">
            <ShieldCheck size={16} />
          </span>
        </div>
        {providerHealth ? (
          <strong className="stat-card-value">
            {healthyProvidersCount}
            <small className="stat-unit">/ {totalProvidersCount}</small>
          </strong>
        ) : (
          <strong className="stat-card-value text-muted">Configured</strong>
        )}
        <p className="stat-card-detail">
          {providerHealth ? `${healthyProvidersCount} healthy services` : 'Live telemetry recorded in process'}
        </p>
      </article>

      {/* 7. Open Incident Alerts */}
      <article className="stat-card stat-card-alert">
        <div className="stat-card-header">
          <span className="stat-card-title">Open Alerts</span>
          <span className="stat-icon stat-icon-amber">
            <Bell size={16} />
          </span>
        </div>
        {busy && alerts.length === 0 ? (
          <div className="skeleton-bar" />
        ) : (
          <strong className="stat-card-value text-amber">
            {String(openAlertsCount).padStart(2, '0')}
          </strong>
        )}
        <p className="stat-card-detail">
          Notifications requiring organization action
        </p>
      </article>

      {/* 8. Classifier Readiness */}
      <article className="stat-card">
        <div className="stat-card-header">
          <span className="stat-card-title">Model Readiness</span>
          <span className="stat-icon stat-icon-purple">
            <AlertTriangle size={16} />
          </span>
        </div>
        {model ? (
          <strong className="stat-card-value stat-value-sm">
            {model.model_available ? 'Trained MVP' : 'Labels Req.'}
          </strong>
        ) : (
          <strong className="stat-card-value stat-value-sm text-muted">Checking…</strong>
        )}
        <p className="stat-card-detail">
          {model?.eligible_labeled_rows != null
            ? `${model.eligible_labeled_rows} labeled rows (30 row gate)`
            : 'Human review workflow'}
        </p>
      </article>
    </div>
  );
}
