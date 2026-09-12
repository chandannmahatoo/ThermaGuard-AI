'use client';
import React, { FormEvent } from 'react';
import { Search, X, Filter, RotateCcw, MapPin } from 'lucide-react';
import type { AreaResult } from '../lib/api';

type FilterToolbarProps = {
  reviewFilter?: string;
  setReviewFilter?: (v:string)=>void;
  classification?: string;
  setClassification?: (v:string)=>void;
  classifications?: string[];
  search: string;
  setSearch: (v: string) => void;
  filter: string;
  setFilter: (v: string) => void;
  sourceFilter: string;
  setSourceFilter: (v: string) => void;
  dateFilter: string;
  setDateFilter: (v: string) => void;
  contextFilter: string;
  setContextFilter: (v: string) => void;
  areaQuery: string;
  setAreaQuery: (v: string) => void;
  areas: AreaResult[];
  area: AreaResult | null;
  setArea: (a: AreaResult | null) => void;
  findArea: (e: FormEvent) => void;
  busy: boolean;
  totalCount: number;
  filteredCount: number;
  onReset?: () => void;
};

export default function FilterToolbar({
  reviewFilter = 'All reviews', setReviewFilter,
  classification = 'All classes', setClassification, classifications = [],
  search,
  setSearch,
  filter,
  setFilter,
  sourceFilter,
  setSourceFilter,
  dateFilter,
  setDateFilter,
  contextFilter,
  setContextFilter,
  areaQuery,
  setAreaQuery,
  areas,
  area,
  setArea,
  findArea,
  busy,
  totalCount,
  filteredCount,
  onReset,
}: FilterToolbarProps) {
  const activeFiltersCount =
    (filter !== 'All risk levels' ? 1 : 0) +
    (sourceFilter !== 'All sensors' ? 1 : 0) +
    (dateFilter !== 'All time' ? 1 : 0) +
    (contextFilter !== 'All events' ? 1 : 0) +
    (area ? 1 : 0) +
    (search.trim() ? 1 : 0) + (classification !== 'All classes' ? 1 : 0) + (reviewFilter !== 'All reviews' ? 1 : 0);

  function resetAll() {
    setReviewFilter?.('All reviews');
    setClassification?.('All classes');
    setAreaQuery('');
    setSearch('');
    setFilter('All risk levels');
    setSourceFilter('All sensors');
    setDateFilter('All time');
    setContextFilter('All events');
    setArea(null);
    if (onReset) onReset();
  }

  return (
    <div className="filter-toolbar-container">
      <div className="filter-toolbar-primary">
        {/* Search input */}
        <div className="filter-search-box">
          <Search size={15} className="filter-search-icon" />
          <input
            type="text"
            aria-label="Search events"
            placeholder="Search event ID, coordinates, town, classification…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button
              type="button"
              className="filter-search-clear"
              aria-label="Clear search input"
              onClick={() => setSearch('')}
            >
              <X size={14} />
            </button>
          )}
        </div>

        {setClassification && <select aria-label="Classification filter" value={classification} onChange={e=>setClassification(e.target.value)}><option>All classes</option>{classifications.map(c=><option key={c} value={c}>{c.replaceAll('_',' ')}</option>)}</select>}
<select aria-label="Review status filter" value={reviewFilter} onChange={e=>setReviewFilter?.(e.target.value)}><option>All reviews</option><option>Reviewed candidate</option><option>Pending candidate</option><option>Unavailable</option></select>
        {/* Risk filter */}
        <div className="filter-select-group">
          <select
            aria-label="Risk filter"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="All risk levels">All Risk Levels</option>
            <option value="Critical">Critical Risk (&gt;80)</option>
            <option value="High">High Risk</option>
            <option value="Medium">Medium Risk</option>
            <option value="Normal">Normal Risk</option>
          </select>
        </div>

        {/* Sensor source filter */}
        <div className="filter-select-group">
          <select
            aria-label="Sensor source filter"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
          >
            <option value="All sensors">All Sensors</option>
            <option value="VIIRS only">VIIRS (375m)</option>
            <option value="MODIS only">MODIS (1km)</option>
            <option value="Cross-sensor">Cross-Sensor Confirmed</option>
          </select>
        </div>

        {/* Observation age filter */}
        <div className="filter-select-group">
          <select
            aria-label="Observation age filter"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
          >
            <option value="All time">All Time Window</option>
            <option value="24 hours">Last 24 Hours</option>
            <option value="7 days">Last 7 Days</option>
            <option value="30 days">Last 30 Days</option>
          </select>
        </div>

        {/* Context completeness filter */}
        <div className="filter-select-group">
          <select
            aria-label="Context availability filter"
            value={contextFilter}
            onChange={(e) => setContextFilter(e.target.value)}
          >
            <option value="All events">All Context States</option>
            <option value="OSM context">OSM Industrial Enriched</option>
            <option value="Satellite context">Copernicus / NDVI Enriched</option>
            <option value="Weather">Weather Available</option>
            <option value="Air quality">Air Quality Available</option>
            <option value="Location">Geocoding Available</option>
            <option value="EONET match">EONET Hazard Match</option>
            <option value="Missing context">Missing Key Context</option>
          </select>
        </div>

        {/* Active filter count & reset */}
        {activeFiltersCount > 0 && (
          <button
            type="button"
            className="filter-reset-button"
            onClick={resetAll}
            title="Reset all active filters"
          >
            <RotateCcw size={13} />
            Reset ({activeFiltersCount})
          </button>
        )}
      </div>

      <div className="filter-chips">{[[reviewFilter!=='All reviews'?reviewFilter:'',()=>setReviewFilter?.('All reviews')],[search,()=>setSearch('')],[filter!=='All risk levels'?filter:'',()=>setFilter('All risk levels')],[sourceFilter!=='All sensors'?sourceFilter:'',()=>setSourceFilter('All sensors')],[dateFilter!=='All time'?dateFilter:'',()=>setDateFilter('All time')],[contextFilter!=='All events'?contextFilter:'',()=>setContextFilter('All events')],[classification!=='All classes'?classification:'',()=>setClassification?.('All classes')]].map(([text,clear],i)=>text ? <button className="button" key={i} type="button" onClick={clear as ()=>void} aria-label={`Remove ${text} filter`}>{String(text)} ×</button>:null)}</div>
      {/* Area Search Sub-bar */}
      <form className="filter-area-bar" onSubmit={findArea}>
        <div className="filter-area-input-wrap">
          <MapPin size={14} className="filter-area-icon" />
          <input
            aria-label="State or city"
            value={areaQuery}
            onChange={(e) => setAreaQuery(e.target.value)}
            placeholder="Focus geographic area (e.g. Maharashtra, Odisha, Delhi)…"
            minLength={2}
          />
        </div>
        <button
          type="submit"
          className="button filter-area-submit"
          disabled={busy || !areaQuery.trim()}
        >
          {busy ? 'Searching…' : 'Locate Area'}
        </button>

        {areas.length > 0 && (
          <select
            aria-label="Select geographic area"
            value={area?.name || ''}
            onChange={(e) =>
              setArea(areas.find((a) => a.name === e.target.value) || null)
            }
            className="filter-area-dropdown"
          >
            <option value="">Select matched territory ({areas.length})</option>
            {areas.map((a) => (
              <option key={a.name} value={a.name}>
                {a.name}
              </option>
            ))}
          </select>
        )}

        {area && (
          <div className="filter-active-area-chip">
            <span>Area: <b>{area.name}</b></span>
            <button
              type="button"
              aria-label="Clear area filter"
              onClick={() => setArea(null)}
            >
              <X size={13} />
            </button>
          </div>
        )}

        <div className="filter-result-counter">
          Showing <b>{filteredCount}</b> of <b>{totalCount}</b> events
        </div>
      </form>
    </div>
  );
}
