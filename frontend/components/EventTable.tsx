'use client';
import React, { useState, useMemo } from 'react';
import {
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Flame,
  Layers,
  MapPin,
  Clock,
  Radio,
} from 'lucide-react';
import type { ThermalEvent } from '../lib/api';
import ContextCoverage from './ContextCoverage';
import { RiskBadge } from './StatusBadge';

type EventTableProps = {
  events: ThermalEvent[];
  selectedId: string | null | undefined;
  onSelect: (e: ThermalEvent) => void;
  busy: boolean;
};

type SortField = 'risk' | 'frp' | 'detections' | 'time';
type SortOrder = 'asc' | 'desc';

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

export default function EventTable({ events, selectedId, onSelect, busy }: EventTableProps) {
  const [sortField, setSortField] = useState<SortField>('risk');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  }

  const sortedEvents = useMemo(() => {
    const list = [...events];
    list.sort((a, b) => {
      let aVal = 0;
      let bVal = 0;
      if (sortField === 'risk') {
        aVal = a.risk?.risk_score ?? 0;
        bVal = b.risk?.risk_score ?? 0;
      } else if (sortField === 'frp') {
        aVal = typeof a.mean_frp === 'number' ? a.mean_frp : 0;
        bVal = typeof b.mean_frp === 'number' ? b.mean_frp : 0;
      } else if (sortField === 'detections') {
        aVal = a.detection_count ?? 0;
        bVal = b.detection_count ?? 0;
      } else if (sortField === 'time') {
        aVal = new Date(a.last_seen_time || 0).getTime();
        bVal = new Date(b.last_seen_time || 0).getTime();
      }
      return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
    });
    return list;
  }, [events, sortField, sortOrder]);

  const totalPages = Math.max(1, Math.ceil(sortedEvents.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const paginatedEvents = sortedEvents.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="event-table-wrapper" aria-busy={busy}>
      <div className="event-sort-controls"><label>Sort events <select value={sortField} onChange={e=>{setSortField(e.target.value as SortField);setPage(1)}}><option value="risk">Risk score</option><option value="frp">Mean FRP</option><option value="detections">Detection count</option><option value="time">Last observed</option></select></label><button className="button" onClick={()=>setSortOrder(sortOrder==='asc'?'desc':'asc')}>{sortOrder==='asc'?'Ascending':'Descending'}</button>{busy&&<span role="status">Refreshing results…</span>}</div>
      <div className="table-responsive-container">
        <table className="geospatial-table">
          <thead>
            <tr>
              <th>Event ID</th>
              <th>Geographic Location</th>
              <th>ML Classification</th>
              <th
                className="sortable-header"
                tabIndex={0}
                onKeyDown={e=>{if(e.key==='Enter' || e.key===' '){e.preventDefault();e.currentTarget.click()}}}
                onClick={() => handleSort('risk')}
                aria-sort={sortField==='risk'?(sortOrder==='asc'?'ascending':'descending'):'none'}
                title="Sort by deterministic risk score"
              >
                <div className="header-cell-sort">
                  <span>Risk Level</span>
                  {sortField === 'risk' && (sortOrder === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </div>
              </th>
              <th
                className="sortable-header"
                tabIndex={0}
                onKeyDown={e=>{if(e.key==='Enter' || e.key===' '){e.preventDefault();e.currentTarget.click()}}}
                onClick={() => handleSort('frp')}
                aria-sort={sortField==='frp'?(sortOrder==='asc'?'ascending':'descending'):'none'}
                title="Sort by mean fire radiative power"
              >
                <div className="header-cell-sort">
                  <span>Mean FRP</span>
                  {sortField === 'frp' && (sortOrder === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </div>
              </th>
              <th
                className="sortable-header"
                tabIndex={0}
                onKeyDown={e=>{if(e.key==='Enter' || e.key===' '){e.preventDefault();e.currentTarget.click()}}}
                onClick={() => handleSort('detections')}
                aria-sort={sortField==='detections'?(sortOrder==='asc'?'ascending':'descending'):'none'}
                title="Sort by detection count"
              >
                <div className="header-cell-sort">
                  <span>Sensors / Detections</span>
                  {sortField === 'detections' && (sortOrder === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </div>
              </th>
              <th>Persistence / sources</th><th>First Seen</th><th>Review Status</th><th>Context Coverage</th>
              <th
                className="sortable-header"
                tabIndex={0}
                onKeyDown={e=>{if(e.key==='Enter' || e.key===' '){e.preventDefault();e.currentTarget.click()}}}
                onClick={() => handleSort('time')}
                aria-sort={sortField==='time'?(sortOrder==='asc'?'ascending':'descending'):'none'}
                title="Sort by last observed timestamp"
              >
                <div className="header-cell-sort">
                  <span>Last Observed</span>
                  {sortField === 'time' && (sortOrder === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />)}
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {busy && events.length === 0 ? (
              <tr>
                <td colSpan={11} className="table-loading-cell">
                  <div className="table-skeleton-row" />
                  <div className="table-skeleton-row" />
                  <div className="table-skeleton-row" />
                </td>
              </tr>
            ) : paginatedEvents.length === 0 ? (
              <tr>
                <td colSpan={11} className="table-empty-cell">
                  <Radio size={24} className="empty-icon" />
                  <p>No thermal events match the current filters.</p>
                </td>
              </tr>
            ) : (
              paginatedEvents.map((e) => {
                const isSelected = selectedId === e.id;
                const isCrossSensor = e.sensor_summary?.cross_sensor_confirmed === true;
                const hasWeather = e.context?.weather?.status === 'available';
                const hasAirQuality = e.context?.air_quality?.status === 'available';
                const hasOsm = e.context?.osm_context_available === true;
                const hasSatellite = e.context?.satellite_context_available === true;
                const hasLocation = e.context?.location?.status === 'available';

                return (
                  <tr
                    key={e.id}
                    tabIndex={0}
                    aria-selected={isSelected}
                    onKeyDown={ev=>{if(ev.key==='ArrowDown'||ev.key==='ArrowUp'){ev.preventDefault();const row=ev.key==='ArrowDown'?ev.currentTarget.nextElementSibling:ev.currentTarget.previousElementSibling;(row as HTMLElement|null)?.focus()}else if(ev.key==='Enter'&&ev.target===ev.currentTarget){onSelect(e)}}}
                    className={`geospatial-row ${isSelected ? 'row-selected' : ''}`}
                    onClick={() => onSelect(e)}
                  >
                    {/* Event ID */}
                    <td className="cell-id">
                      <button
                        type="button"
                        className="table-id-link"
                        onClick={(ev) => {
                          ev.stopPropagation();
                          onSelect(e);
                        }}
                      >
                        {e.is_demo ? 'DEMO · ' : ''}
                        {e.id.length > 20 ? `${e.id.slice(0, 18)}…` : e.id}
                      </button>
                    </td>

                    {/* Location */}
                    <td className="cell-location">
                      {e.context?.location?.status === 'available' && e.context.location.display_name ? (
                        <div className="location-name-truncate" title={e.context.location.display_name}>
                          {e.context.location.display_name}
                        </div>
                      ) : (
                        <span className="text-muted">
                          {num(e.latitude, 3, '?')}°, {num(e.longitude, 3, '?')}°
                        </span>
                      )}
                    </td>

                    {/* ML Classification */}
                    <td className="cell-class">
                      <span className="class-label">
                        {e.classification?.predicted_class
                          ? e.classification.predicted_class.replace(/_/g, ' ')
                          : 'Unclassified'}
                      </span>
                      {typeof e.classification?.classification_confidence === 'number' && (
                        <small className="confidence-tag">
                          {(e.classification.classification_confidence * 100).toFixed(0)}%
                        </small>
                      )}
                    </td>

                    {/* Risk Level & Score */}
                    <td className="cell-risk">
                      <div className="risk-cell-group">
                        <RiskBadge level={e.risk?.risk_level} />
                        <span className="risk-score-pill">{num(e.risk?.risk_score, 0, '—')}</span>
                      </div>
                    </td>

                    {/* Mean FRP */}
                    <td className="cell-frp">
                      <span className="frp-number">{num(e.mean_frp, 1)}</span>
                      <small className="unit-label">MW</small>
                    </td>

                    {/* Sensors / Detections */}
                    <td className="cell-sensors">
                      <div className="sensors-tag-group">
                        <span>{e.detection_count ?? '—'} obs</span>
                        {isCrossSensor && (
                          <span className="cross-sensor-tag" title="Confirmed across multiple satellite sensors">
                            Cross
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Context Coverage Indicators */}
                    <td data-label="Persistence / sources">{e.persistence_days ?? 'Unavailable'} days<br/><small>{Object.keys(e.source_counts||{}).join(', ') || 'Source unavailable'}</small></td><td>{fmtTime(e.start_time)}</td><td><span className="review-state-chip">{e.review_status || 'Not available'}</span><small>Event: {e.status || 'Unavailable'}</small></td>
                    <td className="cell-context">
                      <ContextCoverage context={e.context} compact/>
                    </td>

                    {/* Last Observed */}
                    <td className="cell-time">
                      <span className="time-text">{fmtTime(e.last_seen_time)}</span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="table-pagination-bar">
        <div className="pagination-info">
          Showing <b>{Math.min(events.length, (currentPage - 1) * pageSize + 1)}</b> to{' '}
          <b>{Math.min(events.length, currentPage * pageSize)}</b> of <b>{events.length}</b> events
        </div>
        <div className="pagination-controls">
          <label className="pagination-size-select">
            <span>Per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
            >
              <option value="10">10</option>
              <option value="15">15</option>
              <option value="25">25</option>
              <option value="50">50</option>
            </select>
          </label>
          <button
            type="button"
            className="pagination-btn"
            disabled={currentPage <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="pagination-page-indicator">
            {currentPage} / {totalPages}
          </span>
          <button
            type="button"
            className="pagination-btn"
            disabled={currentPage >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
