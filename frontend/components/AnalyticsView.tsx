'use client';
import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import {
  Activity,
  Layers,
  Flame,
  Radio,
  Clock,
  Shield,
  BarChart3,
} from 'lucide-react';
import type { TrendPoint, ThermalEvent, Alert, ProviderStatusResponse } from '../lib/api';
import {EmptyState,StatRow,useReducedMotion} from './UI';
import {ProviderBadge} from './StatusBadge';
import { RiskBadge } from './StatusBadge';

type AnalyticsViewProps = {
  alerts?: Alert[];
  providers?: ProviderStatusResponse|null;
  reviewedCount?: number;
  trends: TrendPoint[];
  trendsAvailable: boolean;
  trendsReason: string;
  trendsBusy: boolean;
  days: string;
  setDays: (d: string) => void;
  events: ThermalEvent[];
  demo: boolean;
};

export default function AnalyticsView({
  alerts=[],providers,reviewedCount,
  trends,
  trendsAvailable,
  trendsReason,
  trendsBusy,
  days,
  setDays,
  events,
  demo,
}: AnalyticsViewProps) {
  const reducedMotion=useReducedMotion();
  // Classification breakdown
  const classCounts: Record<string, number> = {};
  events.forEach((e) => {
    const c = e.classification?.predicted_class || 'unclassified';
    classCounts[c] = (classCounts[c] || 0) + 1;
  });

  // Sensor counts
  let viirsObservations = 0;
  let modisObservations = 0;
  events.forEach((e) => {
    Object.entries(e.source_counts || {}).forEach(([src, count]) => {
      const s = src.toLowerCase();
      if (s.includes('viirs')) viirsObservations += count;
      else if (s.includes('modis')) modisObservations += count;
    });
  });

  // Context counts
  const osmCount = events.filter((e) => e.context?.osm_context_available).length;
  const satCount = events.filter((e) => e.context?.satellite_context_available).length;
  const weatherCount = events.filter((e) => e.context?.weather?.status === 'available').length;
  const aqCount = events.filter((e) => e.context?.air_quality?.status === 'available').length;

  return (
    <div className="analytics-view-container">
      {/* Trends Section */}
      <section className="analytics-trend-panel">
        <div className="analytics-panel-header">
          <div>
            <h2>Observed Thermal Anomaly Trend</h2>
            <p className="text-muted">
              {demo
                ? 'DEMO DATA · Window ends at the latest fixture observation.'
                : 'Only available satellite observations appear; no missing dates are inferred.'}
            </p>
          </div>
          <div className="analytics-window-select">
            <Clock size={14} className="text-muted" />
            <div className="segmented-control" role="group" aria-label="Analytics period">{[['1','24h'],['7','7d'],['30','30d'],['365','365d']].map(([value,label])=><button type="button" key={value} aria-pressed={days===value} onClick={()=>setDays(value)}>{label}</button>)}</div>
          </div>
        </div>

        <div className="analytics-chart-container">
          {trendsBusy ? (
            <div className="chart-loading-state">
              <Activity size={24} className="spin text-teal" />
              <p>Aggregating verified observation history…</p>
            </div>
          ) : trendsAvailable ? (
            trends.length > 0 ? (
              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={trends} margin={{ top: 15, right: 20, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: 11, fill: '#64748b' }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: '#0f172a',
                        border: '1px solid #334155',
                        borderRadius: '6px',
                        color: '#f8fafc',
                        fontSize: '12px',
                      }}
                      labelStyle={{ color: '#94a3b8', fontWeight: 600 }}
                      formatter={(val: any) => [`${val ?? 0} events`, 'Detected Events']}
                    />
                    <Bar isAnimationActive={!reducedMotion} animationDuration={220} dataKey="events" fill="#0d9488" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState title="No observations recorded" description="No observations recorded in this period. Choose another time window."/>
            )
          ) : (
            <div className="chart-insufficient-history">
              <BarChart3 size={32} className="text-muted" />
              <p>
                Insufficient historical data
                {trendsReason ? ` (${trendsReason.replace(/_/g, ' ')})` : ''}. No chart is shown instead of an incomplete one.
              </p>
            </div>
          )}
        </div>
      </section>

      <section className="analytics-subpanel audit-panel"><h3>Review &amp; delivery audit</h3><div className="audit-tiles"><StatRow label="Reviewed candidates" value={reviewedCount ?? 'Unavailable'}/><StatRow label="Stored alerts" value={alerts.length}/>{['sent','pending','failed','skipped'].map(status=><StatRow key={status} label={`Delivery ${status}`} value={alerts.some(a=>Array.isArray(a.delivery)) ? alerts.reduce((n,a)=>n+(a.delivery?.filter(d=>d.status===status).length || 0),0) : 'Unavailable'}/>)}</div><h4>Provider health</h4><div className="provider-status-list">{providers ? Object.entries(providers.providers).map(([name,p])=><div key={name}><span>{name.replaceAll('_',' ')}</span><ProviderBadge state={p.status}/></div>) : <p>Telemetry unavailable</p>}</div></section>
      {/* Grid of Analytical Breakdowns */}
      <div className="analytics-breakdowns-grid">
        {/* Risk Distribution */}
        <section className="analytics-subpanel">
          <h3>Risk Level Distribution</h3>
          <p className="small text-muted">Authoritative risk bands across all monitored events.</p>
          <div className="risk-level-cards-grid">
            {['Critical', 'High', 'Medium', 'Normal'].map((r) => {
              const count = events.filter((e) => e.risk?.risk_level === r).length;
              return (
                <div key={r} className={`risk-dist-card risk-border-${r.toLowerCase()}`}>
                  <RiskBadge level={r} />
                  <strong className="risk-dist-count">{count}</strong>
                  <span className="risk-dist-pct small">
                    {events.length > 0 ? `${Math.round((count / events.length) * 100)}%` : '0%'}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Classification Distribution */}
        <section className="analytics-subpanel">
          <h3>Machine Learning Classification</h3>
          <p className="small text-muted">RandomForest decision-support classes (model output).</p>
          <div className="class-dist-list">
            {Object.entries(classCounts).map(([className, count]) => (
              <div key={className} className="class-dist-row">
                <span className="class-dist-name">{className.replace(/_/g, ' ')}</span>
                <div className="class-dist-bar-wrap">
                  <div
                    className="class-dist-bar-fill"
                    style={{
                      width: `${events.length > 0 ? (count / events.length) * 100 : 0}%`,
                    }}
                  />
                </div>
                <span className="class-dist-value">
                  {count} ({events.length > 0 ? Math.round((count / events.length) * 100) : 0}%)
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Sensor & Satellite Sources */}
        <section className="analytics-subpanel">
          <h3>Satellite Sensor Observations</h3>
          <p className="small text-muted">Thermal hotspot detections by satellite sensor package.</p>
          <dl className="analytics-dl">
            <div>
              <dt>VIIRS (375m Spatial Resolution)</dt>
              <dd><b>{viirsObservations}</b> hotspot detections</dd>
            </div>
            <div>
              <dt>MODIS (1km Spatial Resolution)</dt>
              <dd><b>{modisObservations}</b> hotspot detections</dd>
            </div>
            <div>
              <dt>Cross-Sensor Confirmed Events</dt>
              <dd>
                <b>{events.filter((e) => e.sensor_summary?.cross_sensor_confirmed === true).length}</b> events
              </dd>
            </div>
          </dl>
        </section>

        {/* Context Coverage Breakdown */}
        <section className="analytics-subpanel">
          <h3>Enriched Geospatial Context</h3>
          <p className="small text-muted">Events enriched with secondary external data sources.</p>
          <dl className="analytics-dl">
            <div>
              <dt>OSM Industrial Features</dt>
              <dd>{osmCount} / {events.length} events</dd>
            </div>
            <div>
              <dt>Copernicus Sentinel-2 NDVI</dt>
              <dd>{satCount} / {events.length} events</dd>
            </div>
            <div>
              <dt>Open-Meteo Weather Grid</dt>
              <dd>{weatherCount} / {events.length} events</dd>
            </div>
            <div>
              <dt>Open-Meteo Air Quality Grid</dt>
              <dd>{aqCount} / {events.length} events</dd>
            </div>
          </dl>
        </section>
      </div>
    </div>
  );
}
