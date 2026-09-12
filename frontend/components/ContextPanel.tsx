'use client';

import { useState } from 'react';

import {
  refreshEventContext,
  apiPost,
  type EventContext,
  type ProviderContext,
  type ThermalEvent,
} from '../lib/api';

const titles: Record<string, string> = {
  location: 'Location',
  weather: 'Weather',
  air_quality: 'Air quality',
  eonet: 'Natural hazard context',
  routing: 'Road access',
};

const fields: Record<string, string> = {
  display_name: 'Location',
  city: 'City',
  district: 'District',
  state: 'State',
  country: 'Country',
  country_code: 'Country code',

  temperature_c: 'Temperature (°C)',
  relative_humidity_percent: 'Relative humidity (%)',
  precipitation_mm: 'Precipitation (mm)',
  wind_speed_kmh: 'Wind speed (km/h)',
  wind_direction_deg: 'Wind direction (°)',
  weather_dataset: 'Weather dataset',

  pm2_5: 'PM2.5 (μg/m³)',
  pm10: 'PM10 (μg/m³)',
  carbon_monoxide: 'CO (μg/m³)',
  nitrogen_dioxide: 'NO₂ (μg/m³)',
  ozone: 'Ozone (μg/m³)',
  air_quality_dataset: 'Air-quality dataset',
  units: 'Units',

  matched: 'Nearby hazard match',
  event_id: 'Hazard ID',
  title: 'Hazard',
  category: 'Category',
  distance_km: 'Distance (km)',
  event_date: 'Hazard date',

  observed_at: 'Context hour (UTC)',
  data_kind: 'Data kind',
  attribution: 'Attribution',

  distance_m: 'Road distance (m)',
  duration_seconds: 'Estimated driving time (s)',
};

type ContextPanelProps = {
  section?: string;
  event: ThermalEvent;
  token: string;
  onRoute: (packet: ProviderContext) => void;
  onContext: (context: EventContext) => void;
};

function readableReason(packet: ProviderContext | undefined): string {
  const reason = packet?.reason ?? packet?.refresh_reason;

  return typeof reason === 'string' && reason
    ? reason.replaceAll('_', ' ')
    : 'Not enriched yet';
}

export default function ContextPanel({
  event,
  token,
  onRoute,
  onContext,
  section,
}: ContextPanelProps) {
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');

  const [routeBusy, setRouteBusy] = useState(false);
  const [routeError, setRouteError] = useState('');

  const [contextBusy, setContextBusy] = useState(false);
  const [contextError, setContextError] = useState('');

  const canRefresh =
    !event.is_demo &&
    (section === 'location' ||
      section === 'weather' ||
      section === 'air_quality' ||
      !section);

  async function refreshContext() {
    if (contextBusy || event.is_demo) return;

    setContextBusy(true);
    setContextError('');

    try {
      const response = await refreshEventContext(event.id, token, 65000);
      onContext(response.context);
    } catch (error) {
      setContextError(
        error instanceof Error
          ? error.message
          : 'External context refresh unavailable',
      );
    } finally {
      setContextBusy(false);
    }
  }

  async function route() {
    if (routeBusy) return;

    setRouteBusy(true);
    setRouteError('');

    try {
      const latitude = Number(lat);
      const longitude = Number(lon);

      if (
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude) ||
        latitude < -90 ||
        latitude > 90 ||
        longitude < -180 ||
        longitude > 180
      ) {
        throw new Error('Enter valid destination coordinates.');
      }

      const packet = await apiPost<ProviderContext>(
        '/events/' + encodeURIComponent(event.id) + '/route',
        {
          latitude,
          longitude,
        },
        token,
        65000,
      );

      onRoute(packet);
    } catch (error) {
      setRouteError(
        error instanceof Error ? error.message : 'Route unavailable',
      );
    } finally {
      setRouteBusy(false);
    }
  }

  return (
    <section>
      <h3>{section ? titles[section] ?? 'External evidence' : 'External evidence'}</h3>

      {canRefresh && (
        <div className="context-refresh">
          <button
            className="button"
            type="button"
            disabled={contextBusy || event.is_demo}
            onClick={refreshContext}
          >
            {contextBusy ? 'Refreshing context…' : 'Refresh event context'}
          </button>

          <p className="small">
            Refreshes Weather, Air Quality, and reverse-geocoded Location for
            this event only.
          </p>

          {contextError && <p role="alert">{contextError}</p>}
        </div>
      )}

      {Object.entries(titles)
        .filter(([key]) => !section || section === key)
        .map(([key, title]) => {
          const packet = event.context?.[key] as ProviderContext | undefined;
          const status =
            key === 'routing' && routeBusy
              ? 'loading'
              : packet?.status || 'unavailable';

          return (
            <details key={key} open={Boolean(section) || key === 'location'}>
              <summary>
                {title} · {status}
              </summary>

              {packet?.status === 'available' ? (
                <>
                  {key === 'eonet' && packet.matched === false && (
                    <p>NASA EONET: No nearby matching hazard</p>
                  )}

                  <dl>
                    {Object.entries(fields)
                      .filter(([field]) => field in packet)
                      .map(([field, label]) => {
                        const value = packet[field];

                        return (
                          <div key={field}>
                            <dt>{label}</dt>
                            <dd>
                              {value === null || value === undefined
                                ? 'Not available'
                                : typeof value === 'boolean'
                                  ? value
                                    ? 'Yes'
                                    : 'No'
                                  : String(value)}
                            </dd>
                          </div>
                        );
                      })}
                  </dl>

                  {packet.refresh_status && (
                    <p className="small">
                      Refresh {String(packet.refresh_status)}
                      {packet.refresh_reason
                        ? ` · ${String(packet.refresh_reason).replaceAll('_', ' ')}`
                        : ''}
                      . Showing the latest retained context.
                    </p>
                  )}

                  <p className="small">
                    {String(packet.provider || 'Provider unavailable')} · Retrieved{' '}
                    {String(packet.fetched_at || 'time unavailable')}
                    {packet.attribution
                      ? ' · ' + String(packet.attribution)
                      : ''}
                  </p>

                  {key === 'eonet' && (
                    <p className="small">
                      Point hazards within the configured distance/time window;
                      supporting context, not classification.
                    </p>
                  )}

                  {(key === 'weather' || key === 'air_quality') && (
                    <p className="small">
                      Modelled grid context for the event hour; not an on-site
                      measurement.
                    </p>
                  )}
                </>
              ) : (
                <p>{readableReason(packet)}</p>
              )}
            </details>
          );
        })}

      {(!section || section === 'routing') && (
        <details open={section === 'routing'}>
          <summary>Route to a response point</summary>

          <p className="small">
            Enter a known destination. Routing must be enabled on the backend.
            A road route does not confirm safe emergency access.
          </p>

          <label>
            Destination latitude
            <input
              aria-label="Destination latitude"
              type="number"
              min="-90"
              max="90"
              step="any"
              value={lat}
              onChange={(event) => setLat(event.target.value)}
            />
          </label>

          <label>
            Destination longitude
            <input
              aria-label="Destination longitude"
              type="number"
              min="-180"
              max="180"
              step="any"
              value={lon}
              onChange={(event) => setLon(event.target.value)}
            />
          </label>

          <button
            className="button"
            type="button"
            disabled={
              routeBusy ||
              !lat.trim() ||
              !lon.trim() ||
              !Number.isFinite(Number(lat)) ||
              !Number.isFinite(Number(lon)) ||
              Math.abs(Number(lat)) > 90 ||
              Math.abs(Number(lon)) > 180 ||
              event.is_demo
            }
            onClick={route}
          >
            {routeBusy ? 'Loading route…' : 'Find road route'}
          </button>

          {routeError && <p role="alert">{routeError}</p>}
        </details>
      )}
    </section>
  );
}
