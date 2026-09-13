import type {ThermalEvent} from './api';
/** Screen-scale grouping for dense views; original events and coordinates remain unchanged. */
export function groupMapEvents(events:ThermalEvent[],zoom:number,selectedId?:string){
 const valid=events.filter(e=>Number.isFinite(e.latitude)&&Math.abs(e.latitude)<=90&&Number.isFinite(e.longitude)&&Math.abs(e.longitude)<=180);
 if(valid.length<80||zoom>=11)return valid.map(event=>[event]);
 const size=360/2**zoom/5;
 const groups=new Map<string,ThermalEvent[]>();
 for(const event of valid){const key=event.id===selectedId?`selected:${event.id}`:`${Math.floor(event.longitude/size)}:${Math.floor(event.latitude/size)}`;const group=groups.get(key)||[];group.push(event);groups.set(key,group)}
 return [...groups.values()];
}
