import React from 'react';
import type { EventContext } from '../lib/api';
export const CONTEXT_KEYS = ['weather', 'air_quality', 'location', 'osm', 'satellite', 'eonet', 'routing'] as const;
const names = ['Weather', 'Air quality', 'Location', 'OSM', 'Satellite', 'EONET', 'Routing'];
export function availableContext(context: EventContext = {}) {
  return CONTEXT_KEYS.map(key => key === 'osm' ? context.osm_context_available === true : key === 'satellite' ? context.satellite_context_available === true : (context[key] as {status?: string} | undefined)?.status === 'available');
}
export default function ContextCoverage({context, compact = false}: {context: EventContext; compact?: boolean}) {
  const available = availableContext(context);
  if (compact) return <span className={available.some(Boolean)?'dot-active':'text-muted'} title={names.map((name,i)=>`${name}: ${available[i]?'available':'not available'}`).join(' · ')}>{available.filter(Boolean).length} / 7</span>;
  return <div className="context-coverage" aria-label="Context coverage"><b>{available.filter(Boolean).length} / 7 available</b><div>{names.map((name, i) => <span key={name} className={available[i] ? 'dot-active' : 'text-muted'}>{name} {available[i] ? '✓' : '—'}</span>)}</div></div>;
}
