import React from 'react';
import type {ThermalEvent, Alert, FirmsStatus, ProviderStatusResponse, ModelStatus} from '../lib/api';
export default function OperationalSummary({events,alerts,firms,providers,backendOk,model}:{events:ThermalEvent[];alerts:Alert[];firms:FirmsStatus|null;providers:ProviderStatusResponse|null;backendOk:boolean|null;model:ModelStatus|null}) {
  const activity = [
    ...events.map(e=>({id:`event-${e.id}`,at:e.last_seen_time,text:`Observation · ${e.id} · ${e.risk.risk_level}`})),
    ...alerts.map(a=>({id:`alert-${a.id}`,at:a.created_at,text:`Alert · ${a.event_id} · ${a.status}`})),
    ...Object.entries(providers?.providers || {}).filter(([,p])=>p.last_failure).map(([name,p])=>({id:`provider-${name}`,at:p.last_failure!,text:`${name} · ${p.last_error_category || 'Recorded failure'}`})),
    ...(firms?.last_success ? [{id:'sync',at:firms.last_success,text:'Successful FIRMS synchronization'}]:[]),
  ].filter(a=>Number.isFinite(Date.parse(a.at))).sort((a,b)=>Date.parse(b.at)-Date.parse(a.at)).slice(0,5);
  return <section className="operational-summary"><div className="review-card"><h2>Operational state</h2><dl className="review-meta-dl"><div><dt>Backend</dt><dd>{backendOk===true?'Reachable':backendOk===false?'Offline':'Unverified'}</dd></div><div><dt>FIRMS</dt><dd>{firms?.available?'Available':firms?.reason || 'Unavailable'}</dd></div><div><dt>Classifier</dt><dd>{model ? model.model_available ? model.model_version : model.reason : 'Unavailable'}</dd></div><div><dt>Gemini</dt><dd>{providers?.providers.gemini?.status || 'Telemetry unavailable'}</dd></div><div><dt>Email / Push</dt><dd>{providers?.providers.smtp?.status || 'Unknown'} / {providers?.providers.firebase?.status || 'Unknown'}</dd></div></dl></div><div className="review-card"><h2>Recent recorded activity</h2>{activity.length ? <ul>{activity.map(a=><li key={a.id}><p>{a.text}</p><time dateTime={a.at}>{new Date(a.at).toISOString().replace('T',' ').replace('.000Z',' UTC')}</time></li>)}</ul>:<p>No activity available.</p>}</div></section>;
}
