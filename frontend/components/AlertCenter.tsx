'use client';
import React, { useState } from 'react';
import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  Clock,
  MapPin,
  Mail,
  Smartphone,
  Check,
  Filter,
} from 'lucide-react';
import type { Alert, AlertDelivery } from '../lib/api';
import { RiskBadge } from './StatusBadge';

type AlertCenterProps = {
  alerts: Alert[];
  onAcknowledge: (id: number) => void;
  ackBusy: number | null;
  onSelectEvent: (eventId: string) => void;
  busy: boolean;
};

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

export default function AlertCenter({
  alerts,
  onAcknowledge,
  ackBusy,
  onSelectEvent,
  busy,
}: AlertCenterProps) {
  const [statusFilter, setStatusFilter] = useState<'all' | 'open' | 'acknowledged'>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const filteredAlerts = alerts.filter((a) => {
    if (statusFilter === 'open' && a.status === 'acknowledged') return false;
    if (statusFilter === 'acknowledged' && a.status !== 'acknowledged') return false;
    if (severityFilter !== 'all' && a.risk_level !== severityFilter) return false;
    return true;
  });

  const openCount = alerts.filter((a) => a.status === 'open').length;
  const acknowledgedCount = alerts.filter((a) => a.status === 'acknowledged').length;

  return (
    <div className="alert-center-container">
      {/* Alert Header & Filters */}
      <div className="alert-center-header">
        <div>
          <h2>Incident Alert Center</h2>
          <p className="text-muted">
            Location-aware notifications dispatched when thermal anomalies cross the deterministic risk threshold for an assigned organization.
          </p>
        </div>

        <div className="alert-filter-controls">
          <div className="alert-status-tabs">
            <button
              type="button"
              className={`alert-tab-btn ${statusFilter === 'all' ? 'active' : ''}`}
              onClick={() => setStatusFilter('all')}
            >
              All ({alerts.length})
            </button>
            <button
              type="button"
              className={`alert-tab-btn ${statusFilter === 'open' ? 'active' : ''}`}
              onClick={() => setStatusFilter('open')}
            >
              Open ({openCount})
            </button>
            <button
              type="button"
              className={`alert-tab-btn ${statusFilter === 'acknowledged' ? 'active' : ''}`}
              onClick={() => setStatusFilter('acknowledged')}
            >
              Acknowledged ({acknowledgedCount})
            </button>
          </div>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="alert-severity-select"
            aria-label="Filter by alert severity"
          >
            <option value="all">All Severities</option>
            <option value="Critical">Critical Risk</option>
            <option value="High">High Risk</option>
            <option value="Medium">Medium Risk</option>
          </select>
        </div>
      </div>

      {/* Alerts List */}
      <div className="alerts-feed">
        {busy && alerts.length === 0 ? (
          <div className="alert-loading-skeleton">
            <div className="skeleton-card" />
            <div className="skeleton-card" />
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="alerts-empty-state">
            <CheckCircle2 size={36} className="empty-check-icon" />
            <h3>No incidents match your filter</h3>
            <p className="text-muted">
              {alerts.length === 0
                ? 'No alerts in your assigned scope. Alerts trigger deterministically when monitored thermal anomalies cross the risk threshold.'
                : 'All qualifying alerts in this view have been reviewed.'}
            </p>
          </div>
        ) : (
          filteredAlerts.map((a) => {
            const isAcknowledged = a.status === 'acknowledged';
            const isBusy = ackBusy === a.id;

            return (
              <article
                key={a.id}
                className={`alert-card ${isAcknowledged ? 'alert-acknowledged' : 'alert-open'}`}
              >
                <div className="alert-card-left">
                  <div className="alert-icon-wrap">
                    <Bell size={20} className={a.risk_level === 'Critical' ? 'text-red' : 'text-amber'} />
                  </div>

                  <div className="alert-details">
                    <div className="alert-title-row">
                      <h3 className="alert-title">
                        {a.is_demo ? 'Demo · ' : ''}
                        {a.risk_level} Risk Notification
                      </h3>
                      <RiskBadge level={a.risk_level} />
                      <span className={`alert-status-chip ${isAcknowledged ? 'chip-ack' : 'chip-open'}`}>
                        {isAcknowledged ? 'Acknowledged' : 'Open Incident'}
                      </span>
                    </div>

                    <div className="alert-meta-row">
                      <button
                        type="button"
                        className="alert-event-id-btn"
                        onClick={() => onSelectEvent(a.event_id)}
                        title="View event in explorer"
                      >
                        <MapPin size={13} />
                        {a.event_id}
                      </button>

                      {typeof a.latitude === 'number' && typeof a.longitude === 'number' && (
                        <span className="alert-coords">
                          ({a.latitude.toFixed(3)}° N, {a.longitude.toFixed(3)}° E)
                        </span>
                      )}

                      <span className="alert-time">
                        <Clock size={13} />
                        {fmtTime(a.created_at)}
                      </span>
                    </div>

                    {/* Delivery Audit Trail */}
                    {Array.isArray(a.delivery) && a.delivery.length > 0 ? (
                      <div className="delivery-audit-trail">
                        <span className="delivery-audit-label">Delivery Audit:</span>
                        {a.delivery.map((d: AlertDelivery, i: number) => {
                          const isSent = d.status === 'sent';
                          return (
                            <span
                              key={i}
                              className={`delivery-chip ${isSent ? 'delivery-ok' : 'delivery-warn'}`}
                            >
                              {d.channel === 'push' ? (
                                <Smartphone size={11} className="delivery-icon" />
                              ) : (
                                <Mail size={11} className="delivery-icon" />
                              )}
                              <span>
                                {d.channel === 'push' ? 'Push' : 'Email'}: {d.status || 'attempting'}
                                {d.sent_at ? ` (${fmtTime(d.sent_at)})` : ''}
                              </span>
                            </span>
                          );
                        })}
                      </div>
                    ) : a.delivery === null ? (
                      <small className="delivery-admin-only-note">
                        Multi-channel delivery audit logs visible to administrators.
                      </small>
                    ) : null}
                  </div>
                </div>

                <div className="alert-card-right">
                  <button
                    type="button"
                    className={`button alert-ack-btn ${isAcknowledged ? 'btn-disabled' : ''}`}
                    disabled={isAcknowledged || isBusy}
                    onClick={() => onAcknowledge(a.id)}
                  >
                    {isAcknowledged ? (
                      <>
                        <Check size={14} />
                        Acknowledged
                      </>
                    ) : isBusy ? (
                      'Acknowledging…'
                    ) : (
                      'Acknowledge'
                    )}
                  </button>
                </div>
              </article>
            );
          })
        )}
      </div>
    </div>
  );
}
