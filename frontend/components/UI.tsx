'use client';
import React, {memo, useEffect, useRef, useState} from 'react';
import {Info, Inbox, AlertCircle} from 'lucide-react';

export function LoadingSkeleton({label='Loading data',lines=3}:{label?:string;lines?:number}) {
  return <div className="loading-skeleton" role="status" aria-label={label}>{Array.from({length:lines},(_,i)=><span className="skeleton-bar" key={i}/>)}</div>;
}
export function EmptyState({title='Nothing to display',description,action}:{title?:string;description:string;action?:React.ReactNode}) {
  return <div className="experience-state"><Inbox aria-hidden size={30}/><h3>{title}</h3><p>{description}</p>{action}</div>;
}
export function ErrorState({message,onRetry}:{message:string;onRetry?:()=>void}) {
  return <div className="experience-state error-state" role="alert"><AlertCircle aria-hidden size={24}/><h3>Unable to load this section</h3><p>{message}</p>{onRetry && <button className="button" onClick={onRetry}>Try again</button>}</div>;
}
export function SectionHeader({title,description,action}:{title:string;description?:string;action?:React.ReactNode}) {
  return <header className="section-heading"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</header>;
}
export function StatRow({label,value}:{label:string;value:React.ReactNode}) {
  return <div className="stat-row"><span>{label}</span><strong>{value}</strong></div>;
}
export function formatMetric(value:number|null|undefined,suffix='') {
  return value == null || !Number.isFinite(value) ? 'Unavailable' : `${String(Math.round(value)).padStart(2,'0')}${suffix}`;
}
export const MetricCard=memo(function MetricCard({title,value,description,icon,suffix='',loading=false,tone='teal'}:{title:string;value:number|null|undefined;description:string;icon?:React.ReactNode;suffix?:string;loading?:boolean;tone?:string}) {
  const [display,setDisplay]=useState(value);
  const animated=useRef(false);
  useEffect(()=>{
    if(value==null || !Number.isFinite(value)) {setDisplay(value);return;}
    if(animated.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches){setDisplay(value);return;}
    animated.current=true;
    const start=performance.now();let frame=0;
    const tick=(time:number)=>{const progress=Math.min(1,(time-start)/220);setDisplay(value*(1-(1-progress)**3));if(progress<1)frame=requestAnimationFrame(tick);};
    frame=requestAnimationFrame(tick);
    return ()=>cancelAnimationFrame(frame);
  },[value]);
  return <article className={`stat-card metric-interactive tone-${tone}`} title={description}><div className="stat-card-header"><span className="stat-card-title">{title}</span><span className={`stat-icon stat-icon-${tone}`}>{icon || <Info size={16}/>}</span></div>{loading?<LoadingSkeleton label={`Loading ${title}`} lines={1}/>:<strong className="stat-card-value" aria-label={formatMetric(value,suffix)}><span aria-hidden="true">{formatMetric(display,suffix)}</span></strong>}<p className="stat-card-detail">{description}</p></article>;
});

export function useReducedMotion() {
  const [reduced,setReduced]=useState(false);
  useEffect(()=>{const query=window.matchMedia('(prefers-reduced-motion: reduce)');const update=()=>setReduced(query.matches);update();query.addEventListener('change',update);return ()=>query.removeEventListener('change',update);},[]);
  return reduced;
}
