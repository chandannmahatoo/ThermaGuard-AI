import type {ThermalEvent,Alert} from '../api';
import type {ReviewCandidate} from '../reviewCandidates';
export const finite=(n:unknown):n is number=>typeof n==='number'&&Number.isFinite(n);
export const display=(value:unknown)=>value==null||value===''?'Unavailable':typeof value==='object'?JSON.stringify(value):String(value);
export function completeness(e:ThermalEvent){
 const checks:[string,boolean][]=[['Thermal detections',finite(e.detection_count)&&e.detection_count>0],['Sensor sources',Object.keys(e.source_counts||{}).length>0],['OSM',e.context?.osm_context_available===true],['Satellite',e.context?.satellite_context_available===true],['Historical baseline',e.risk?.abnormality?.baseline_available===true],['Geocoding',e.context?.location?.status==='available'],['Weather',e.context?.weather?.status==='available'],['Air quality',e.context?.air_quality?.status==='available']];
 return {checks,available:checks.filter(([,ok])=>ok).length,total:checks.length,percent:Math.round(checks.filter(([,ok])=>ok).length/checks.length*100)};
}
export function rankCandidates(candidates:ReviewCandidate[],events:ThermalEvent[]){
 const byId=new Map(events.map(e=>[e.id,e]));const labels:Record<string,number>={};events.forEach(e=>{const c=e.classification?.predicted_class;if(c)labels[c]=(labels[c]||0)+1});
 return candidates.map(candidate=>{const event=byId.get(candidate.event_id);const reasons:string[]=[];let priority=0;
 if(candidate.reviewed.toLowerCase()!=='true'){priority+=10;reasons.push('Unreviewed export')}
 if(candidate.review_stale==='true'){priority+=30;reasons.push('Backend reports stale evidence')}
 const confidence=event?.classification?.classification_confidence;
 if(finite(confidence)&&confidence>=0&&confidence<=1){priority+=(1-confidence)*40;reasons.push(`${Math.round(confidence*100)}% model confidence`)}
 if(event){const quality=completeness(event);priority+=(1-quality.percent/100)*10;if(quality.available<quality.total)reasons.push(`${quality.total-quality.available} UI evidence checks missing`);const label=event.classification?.predicted_class;if(label&&labels[label]){priority+=10/labels[label];reasons.push(`${labels[label]} loaded event(s) in predicted class`)}}
 return {candidate,event,priority:Math.round(priority),reasons};}).sort((a,b)=>b.priority-a.priority||a.candidate.event_id.localeCompare(b.candidate.event_id));
}
export function timeline(e:ThermalEvent,alerts:Alert[],review?:ReviewCandidate){
 const rows:{at:string;label:string}[]=[];const add=(at:string|undefined|null,label:string)=>{if(at&&Number.isFinite(Date.parse(at)))rows.push({at,label})};
 add(e.start_time,'First detection');add(e.last_seen_time,'Last detection');add(review?.reviewed_at,'Recorded human review');
 for(const [name,p] of Object.entries(e.context||{})){if(p&&typeof p==='object'&&'fetched_at' in p)add(String(p.fetched_at),`${name.replaceAll('_',' ')} fetched`)}
 for(const alert of alerts.filter(a=>a.event_id===e.id)){add(alert.created_at,`Alert ${alert.id} generated · ${alert.status}`);for(const delivery of alert.delivery||[])add(delivery.sent_at,`${delivery.channel} · ${delivery.status}`)}
 return rows.sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
}
export function naturalSearch(events:ThermalEvent[],query:string,reviews:ReviewCandidate[],now=Date.now()){
 const q=query.trim().toLowerCase();if(!q)return {supported:true,description:'All loaded events',events};
 let predicate:((e:ThermalEvent)=>boolean)|undefined;let description='';
 const high=q.match(/^high[- ]risk events(?: in (.+))?$/);
 if(high){description='High or Critical risk; optional location text from available geocoding.';predicate=e=>['High','Critical'].includes(e.risk?.risk_level)&&(!high[1]||String(e.context?.location?.display_name||e.context?.location?.state||'').toLowerCase().includes(high[1]))}
 else if(/^persistent thermal sources(?: this week)?$/.test(q)){description='Persistence ≥ 2 days'+(q.endsWith('this week')?'; last observed within the past 7 days.':'.');predicate=e=>finite(e.persistence_days)&&e.persistence_days>=2&&(!q.endsWith('this week')||(Date.parse(e.last_seen_time)>=now-7*864e5&&Date.parse(e.last_seen_time)<=now))}
 else if(q==='unreviewed low-confidence events'){const ids=new Set(reviews.filter(r=>r.reviewed.toLowerCase()!=='true').map(r=>r.event_id));description='Unreviewed export candidates with model confidence below 60%.';predicate=e=>ids.has(e.id)&&finite(e.classification?.classification_confidence)&&e.classification.classification_confidence<.6}
 else if(q==='events close to refineries'){description='Named nearby facilities containing refinery; distance-based refinery filtering is unavailable.';predicate=e=>(e.context?.nearby_facility_names||[]).some(n=>/refiner/i.test(n))}
 return predicate?{supported:true,description,events:events.filter(predicate)}:{supported:false,description:'Pattern unsupported. Use one of the examples; no query was sent to the backend.',events:[]};
}
export function observationTrend(events:ThermalEvent[]){
 const rows=new Map<string,{day:string;events:number;frpTotal:number;frpCount:number;confidenceTotal:number;confidenceCount:number;missing:number}>();
 for(const e of events){if(!Number.isFinite(Date.parse(e.last_seen_time)))continue;const day=new Date(e.last_seen_time).toISOString().slice(0,10);const r=rows.get(day)||{day,events:0,frpTotal:0,frpCount:0,confidenceTotal:0,confidenceCount:0,missing:0};r.events++;if(finite(e.mean_frp)){r.frpTotal+=e.mean_frp;r.frpCount++}if(finite(e.classification?.classification_confidence)){r.confidenceTotal+=e.classification.classification_confidence;r.confidenceCount++}r.missing+=completeness(e).total-completeness(e).available;rows.set(day,r)}
 return [...rows.values()].sort((a,b)=>a.day.localeCompare(b.day)).map(r=>({...r,frp:r.frpCount?r.frpTotal/r.frpCount:null,confidence:r.confidenceCount?r.confidenceTotal/r.confidenceCount:null}));
}
export function lineage(e:ThermalEvent,alerts:Alert[],review?:ReviewCandidate):[string,string][]{return [
 ['FIRMS detection',e.detection_count>0?`${e.detection_count} observations`:'Unavailable'],['Validation','Per-observation audit unavailable'],['Deduplication','Audit unavailable'],['Event clustering',`Event ${e.id}`],['Context enrichment',`${completeness(e).available}/${completeness(e).total} UI checks available`],['Feature engineering',e.classification?.feature_version||'Version unavailable'],['ML classification',e.classification?.predicted_class||'Unavailable'],['Risk assessment',e.risk?.risk_level||'Unavailable'],['Alert',alerts.some(a=>a.event_id===e.id)?'Recorded':'None in loaded alerts'],['Notification',alerts.some(a=>a.event_id===e.id&&(a.delivery||[]).length)?'Delivery records available':'Delivery records unavailable'],['Human review',review?.reviewed||'Unavailable'],['Training dataset','Individual inclusion unavailable']];}

export function freshness(timestamp:unknown,now=Date.now()){if(typeof timestamp!=='string'||!Number.isFinite(Date.parse(timestamp)))return 'Age unavailable';const minutes=Math.floor((now-Date.parse(timestamp))/60000);return minutes<0?'Timestamp is in the future':minutes<60?`${minutes} min old`:minutes<1440?`${Math.floor(minutes/60)} h old`:`${Math.floor(minutes/1440)} d old`;}
