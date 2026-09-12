'use client';
import React, { useState, FormEvent } from 'react';
import {
  Bell,
  Mail,
  Smartphone,
  MapPin,
  Shield,
  Save,
  Users,
  Compass,
  Sliders,
  CheckCircle2,
} from 'lucide-react';
import type { NotificationPreferences, Organization, Assignment } from '../lib/api';

type NotificationSettingsProps = {
  notif: NotificationPreferences | null;
  notifBusy: boolean;
  onSaveNotif: (next: NotificationPreferences) => void;
  isAdmin: boolean;
  organizations: Organization[];
  assignments: Assignment[];
  onCreateOrg: (values: Record<string, string>) => Promise<void>;
  onAssignArea: (values: Record<string, string>) => Promise<void>;
  onUpdateThreshold: (threshold: number) => Promise<void>;
  onAssignUser: (values: Record<string, string>) => Promise<void>;
};

type NotificationFormState = {
  notifications_enabled: boolean;
  latitude: string;
  longitude: string;
  alert_radius_km: number;
};

function normalizeFormState(raw: NotificationPreferences | null): NotificationFormState | null {
  if (!raw) return null;
  return {
    notifications_enabled: Boolean(raw.notifications_enabled),
    latitude: raw.latitude !== null && raw.latitude !== undefined ? String(raw.latitude) : '',
    longitude: raw.longitude !== null && raw.longitude !== undefined ? String(raw.longitude) : '',
    alert_radius_km: typeof raw.alert_radius_km === 'number' && !Number.isNaN(raw.alert_radius_km) ? raw.alert_radius_km : 10,
  };
}

export default function NotificationSettings({
  notif,
  notifBusy,
  onSaveNotif,
  isAdmin,
  organizations,
  assignments,
  onCreateOrg,
  onAssignArea,
  onUpdateThreshold,
  onAssignUser,
}: NotificationSettingsProps) {
  const [formState, setFormState] = useState<NotificationFormState | null>(() => normalizeFormState(notif));
  const [thresholdInput, setThresholdInput] = useState('80');
  const [orgName, setOrgName] = useState('');
  const [orgEmail, setOrgEmail] = useState('');
  const [areaOrgId, setAreaOrgId] = useState('');
  const [areaName, setAreaName] = useState('');
  const [areaBounds, setAreaBounds] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [userOrgId, setUserOrgId] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Sync state when props change
  React.useEffect(() => {
    if (notif) {
      setFormState(normalizeFormState(notif));
    }
  }, [notif]);

  function handleUseBrowserLocation() {
    if (typeof navigator !== 'undefined' && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setFormState((prev) =>
            prev
              ? {
                  ...prev,
                  latitude: pos.coords.latitude.toFixed(4),
                  longitude: pos.coords.longitude.toFixed(4),
                }
              : {
                  notifications_enabled: false,
                  alert_radius_km: 10,
                  latitude: pos.coords.latitude.toFixed(4),
                  longitude: pos.coords.longitude.toFixed(4),
                }
          );
        },
        (err) => {
          alert('Could not acquire location: ' + err.message);
        }
      );
    }
  }

  function handleSavePreferences() {
    if (formState) {
      const parsedLat = formState.latitude.trim() === '' ? null : Number(formState.latitude);
      const parsedLon = formState.longitude.trim() === '' ? null : Number(formState.longitude);
      onSaveNotif({
        notifications_enabled: formState.notifications_enabled,
        latitude: parsedLat !== null && !Number.isNaN(parsedLat) ? parsedLat : null,
        longitude: parsedLon !== null && !Number.isNaN(parsedLon) ? parsedLon : null,
        alert_radius_km: typeof formState.alert_radius_km === 'number' && !Number.isNaN(formState.alert_radius_km) ? formState.alert_radius_km : 10,
      });
    }
  }

  const hasCoordinates =
    formState !== null &&
    formState.latitude.trim() !== '' &&
    formState.longitude.trim() !== '' &&
    !Number.isNaN(Number(formState.latitude)) &&
    !Number.isNaN(Number(formState.longitude));

  return (
    <div className="settings-view-container">
      {/* User Notification Preferences Section */}
      <section className="settings-panel">
        <div className="settings-panel-header">
          <div className="settings-icon-wrap">
            <Bell size={20} className="text-teal" />
          </div>
          <div>
            <h2>Incident Notification Preferences</h2>
            <p className="text-muted">
              Configure your operational monitoring radius and notification channels.
              Alerts trigger deterministically when thermal events exceed risk criteria within your geographic radius.
            </p>
          </div>
        </div>

        {formState ? (
          <div className="settings-form-grid">
            <div className="settings-toggle-card">
              <label className="toggle-switch-label">
                <input
                  type="checkbox"
                  checked={formState.notifications_enabled}
                  disabled={notifBusy}
                  onChange={(e) =>
                    setFormState({ ...formState, notifications_enabled: e.target.checked })
                  }
                />
                <span className="toggle-slider" />
                <span className="toggle-text">
                  <b>Dispatch Multi-Channel Alerts</b> (Email &amp; Mobile Push)
                </span>
              </label>
              <p className="small text-muted">
                {formState.notifications_enabled
                  ? 'Active: you will receive alerts when events cross threshold inside your radius.'
                  : 'Inactive: no automated notifications will be dispatched.'}
              </p>
            </div>

            <div className="settings-input-group">
              <label>
                <span>Alert Radius ({formState.alert_radius_km} km)</span>
                <input
                  type="range"
                  min={1}
                  max={500}
                  step={1}
                  value={formState.alert_radius_km}
                  disabled={notifBusy}
                  onChange={(e) =>
                    setFormState({
                      ...formState,
                      alert_radius_km: Number(e.target.value) || 10,
                    })
                  }
                  className="radius-slider"
                />
              </label>
            </div>

            <div className="settings-coords-row">
              <div className="coord-input-wrap">
                <label>
                  <span>Home Latitude (-90 to 90)</span>
                  <input
                    type="number"
                    min={-90}
                    max={90}
                    step="any"
                    value={formState.latitude}
                    disabled={notifBusy}
                    onChange={(e) =>
                      setFormState({
                        ...formState,
                        latitude: e.target.value,
                      })
                    }
                    placeholder="e.g. 19.076"
                  />
                </label>
              </div>

              <div className="coord-input-wrap">
                <label>
                  <span>Home Longitude (-180 to 180)</span>
                  <input
                    type="number"
                    min={-180}
                    max={180}
                    step="any"
                    value={formState.longitude}
                    disabled={notifBusy}
                    onChange={(e) =>
                      setFormState({
                        ...formState,
                        longitude: e.target.value,
                      })
                    }
                    placeholder="e.g. 72.877"
                  />
                </label>
              </div>

              <button
                type="button"
                className="button coord-geolocate-btn"
                onClick={handleUseBrowserLocation}
                disabled={notifBusy}
                title="Acquire coordinates from browser GPS"
              >
                <Compass size={15} />
                Current GPS
              </button>
            </div>

            <div className="settings-save-actions">
              <button
                type="button"
                className="primary settings-save-btn"
                disabled={notifBusy}
                onClick={handleSavePreferences}
              >
                <Save size={16} />
                {notifBusy ? 'Saving…' : 'Save Notification Preferences'}
              </button>
              {!hasCoordinates ? (
                <span className="text-amber small">
                  A valid geographic location is required to enable localized alerts.
                </span>
              ) : null}
            </div>
          </div>
        ) : (
          <p className="empty">Loading notification preferences…</p>
        )}
      </section>

      {/* Administrator Configuration (Admin only) */}
      {isAdmin && (
        <div className="admin-settings-section">
          <div className="admin-section-title">
            <Shield size={18} className="text-teal" />
            <h2>National Command Administration</h2>
          </div>

          <div className="admin-grid-cards">
            {/* Organizations Management */}
            <section className="settings-subpanel">
              <h3>Registered Organizations</h3>
              <div className="admin-list-scroll">
                {organizations.map((o) => (
                  <div key={o.id} className="admin-list-item">
                    <b>#{o.id} · {o.name}</b>
                    <small className="text-muted">{o.email}</small>
                  </div>
                ))}
                {organizations.length === 0 && (
                  <p className="small text-muted">No organizations registered yet.</p>
                )}
              </div>

              <form
                className="admin-inline-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSubmitting(true);
                  try {
                    await onCreateOrg({ name: orgName, email: orgEmail });
                    setOrgName('');
                    setOrgEmail('');
                  } finally {
                    setSubmitting(false);
                  }
                }}
              >
                <h4>Create Organization</h4>
                <input
                  placeholder="Organization name"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  required
                />
                <input
                  type="email"
                  placeholder="Organization email"
                  value={orgEmail}
                  onChange={(e) => setOrgEmail(e.target.value)}
                  required
                />
                <button type="submit" className="button" disabled={submitting}>
                  {submitting ? 'Creating…' : 'Add Organization'}
                </button>
              </form>
            </section>

            {/* Area Assignments */}
            <section className="settings-subpanel">
              <h3>Territory Assignments</h3>
              <div className="admin-list-scroll">
                {assignments.map((a) => (
                  <div key={a.id} className="admin-list-item">
                    <b>{a.area_name}</b>
                    <small className="text-muted">
                      Org #{a.organization_id} · Bounds: {a.bounds?.join(', ')}
                    </small>
                  </div>
                ))}
                {assignments.length === 0 && (
                  <p className="small text-muted">No territories assigned yet.</p>
                )}
              </div>

              <form
                className="admin-inline-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSubmitting(true);
                  try {
                    await onAssignArea({
                      organization_id: areaOrgId,
                      area_name: areaName,
                      bounds: areaBounds,
                    });
                    setAreaOrgId('');
                    setAreaName('');
                    setAreaBounds('');
                  } finally {
                    setSubmitting(false);
                  }
                }}
              >
                <h4>Assign Territory</h4>
                <input
                  placeholder="Org ID"
                  value={areaOrgId}
                  onChange={(e) => setAreaOrgId(e.target.value)}
                  required
                />
                <input
                  placeholder="Area Name (e.g. Maharashtra)"
                  value={areaName}
                  onChange={(e) => setAreaName(e.target.value)}
                  required
                />
                <input
                  placeholder="Bounds: W, S, E, N"
                  value={areaBounds}
                  onChange={(e) => setAreaBounds(e.target.value)}
                  required
                />
                <button type="submit" className="button" disabled={submitting}>
                  {submitting ? 'Assigning…' : 'Assign Area'}
                </button>
              </form>
            </section>

            {/* Global Threshold Adjustment */}
            <section className="settings-subpanel">
              <h3>Incident Alert Threshold</h3>
              <p className="small text-muted">
                Default score: 80. Events with deterministic risk exceeding this threshold trigger automated dispatch.
              </p>
              <form
                className="admin-inline-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSubmitting(true);
                  try {
                    await onUpdateThreshold(Number(thresholdInput));
                  } finally {
                    setSubmitting(false);
                  }
                }}
              >
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={thresholdInput}
                  onChange={(e) => setThresholdInput(e.target.value)}
                  required
                />
                <button type="submit" className="button" disabled={submitting}>
                  {submitting ? 'Updating…' : 'Update Threshold'}
                </button>
              </form>

              <h4 style={{ marginTop: '20px' }}>Connect Registered User</h4>
              <form
                className="admin-inline-form"
                onSubmit={async (e) => {
                  e.preventDefault();
                  setSubmitting(true);
                  try {
                    await onAssignUser({ email: userEmail, organization_id: userOrgId });
                    setUserEmail('');
                    setUserOrgId('');
                  } finally {
                    setSubmitting(false);
                  }
                }}
              >
                <input
                  type="email"
                  placeholder="User email"
                  value={userEmail}
                  onChange={(e) => setUserEmail(e.target.value)}
                  required
                />
                <input
                  placeholder="Org ID"
                  value={userOrgId}
                  onChange={(e) => setUserOrgId(e.target.value)}
                  required
                />
                <button type="submit" className="button" disabled={submitting}>
                  {submitting ? 'Connecting…' : 'Assign User'}
                </button>
              </form>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
