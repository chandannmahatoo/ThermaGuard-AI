'use client';
import React from 'react';
import {Flame,ScanLine,Layers,ShieldCheck,Radio,FileCheck,Satellite,AlertTriangle} from 'lucide-react';
import type {ThermalEvent,Alert,ModelStatus,ProviderStatusResponse} from '../lib/api';
import {MetricCard} from './UI';
import {availableContext} from './ContextCoverage';
type Props={events:ThermalEvent[];alerts:Alert[];model:ModelStatus|null;providerHealth:ProviderStatusResponse|null;busy:boolean;demo:boolean;reviewedCount?:number;dataAvailable?:boolean};
export default function OverviewKPIs({events,providerHealth,busy,demo,reviewedCount,dataAvailable=true}:Props){
  const available=dataAvailable && !(!events.length && busy);
  const total=events.length;
  const enriched=events.filter(e=>availableContext(e.context).some(Boolean)).length;
  const providers=providerHealth?Object.values(providerHealth.providers):null;
  const metrics=[
    {title:'Monitored Events',value:available?total:null,description:`Stored events in your monitoring scope${demo?' · Demo data':''}`,icon:<ScanLine size={17}/>},
    {title:'Critical Events',value:available?events.filter(e=>e.risk?.risk_level==='Critical').length:null,description:'Backend-assigned Critical risk band',icon:<Flame size={17}/>,tone:'red'},
    {title:'High-Risk Events',value:available?events.filter(e=>e.risk?.risk_level==='High').length:null,description:'Backend-assigned High risk band',icon:<AlertTriangle size={17}/>,tone:'amber'},
    {title:'FIRMS Detections',value:available?events.reduce((n,e)=>n+e.detection_count,0):null,description:'Satellite observations within monitored events',icon:<Satellite size={17}/>,tone:'blue'},
    {title:'Reviewed Events',value:reviewedCount,description:'Recorded human reviews in candidate dataset',icon:<FileCheck size={17}/>},
    {title:'Cross-Sensor Events',value:available?events.filter(e=>e.sensor_summary?.cross_sensor_confirmed===true).length:null,description:'Backend-confirmed multi-sensor evidence',icon:<Layers size={17}/>,tone:'blue'},
    {title:'Context Coverage',value:available&&total?Math.round(enriched/total*100):null,suffix:'%',description:`${enriched} of ${total} events have at least one available context source`,icon:<Radio size={17}/>},
    {title:'Providers Healthy',value:providers?.filter(p=>p.status==='healthy').length,description:providers?`${providers.length} providers with reported telemetry`:'Provider telemetry unavailable',icon:<ShieldCheck size={17}/>,tone:'green'},
  ];
  return <div className="stats-kpi-grid">{metrics.map(metric=><MetricCard key={metric.title} {...metric} loading={busy&&!events.length}/>)}</div>;
}
