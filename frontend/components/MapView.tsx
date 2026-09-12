'use client';
import {MapContainer,TileLayer,CircleMarker,Polyline,Tooltip,useMap} from 'react-leaflet';
import {useEffect} from 'react';
import type {ThermalEvent,RawDetection,EonetHazard} from '../lib/api';

const colors:Record<string,string>={Critical:'#ef4444',High:'#f97316',Medium:'#eab308',Normal:'#10b981'};
const colorFor=(level:string|undefined)=>colors[level||'']||'#94a3b8';

function Focus({selected}:{selected:ThermalEvent|null}){
  const map=useMap();
  useEffect(()=>{
    if(selected)map.flyTo([selected.latitude,selected.longitude],8,{duration:0.8});
    else map.fitBounds([[6,68],[37,98]],{padding:[20,20]});
  },[selected,map]);
  return null;
}

export type MapViewProps={
  detections?:RawDetection[];
  events:ThermalEvent[];
  onSelect:(e:ThermalEvent)=>void;
  selected:ThermalEvent|null;
  hazards?:EonetHazard[];
  showHazards?:boolean;
  showIndustrial?:boolean;
  subscriberLocation?:{latitude:number;longitude:number;radiusKm:number}|null;
  showSubscriberRadius?:boolean;
};

export default function MapView({events,onSelect,selected,detections,hazards,showHazards,showIndustrial,subscriberLocation,showSubscriberRadius}:MapViewProps){
  return (
    <MapContainer center={[22.5,79.5]} zoom={5} minZoom={3} maxZoom={18} style={{height:'100%',width:'100%'}}>
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"/>
      <Focus selected={selected}/>

      {/* Subscriber notification radius overlay */}
      {showSubscriberRadius && subscriberLocation?.latitude && subscriberLocation?.longitude && (
        <CircleMarker
          center={[subscriberLocation.latitude, subscriberLocation.longitude]}
          radius={Math.min(100, Math.max(16, subscriberLocation.radiusKm * 1.5))}
          pathOptions={{color:'#38bdf8',fillColor:'#0284c7',fillOpacity:0.12,weight:2,dashArray:'6 6'}}
        >
          <Tooltip direction="top">Subscriber Alert Zone<br/>Radius: {subscriberLocation.radiusKm} km around home coordinates</Tooltip>
        </CircleMarker>
      )}

      {/* Road route line from OpenRouteService */}
      {selected?.context?.routing?.status==='available' && selected.context.routing.geometry?.type==='LineString' && (
        <Polyline positions={selected.context.routing.geometry.coordinates.map(([lon,lat])=>[lat,lon])} pathOptions={{color:'#38bdf8',weight:4,opacity:0.85}}/>
      )}

      {/* NASA EONET natural hazards layer */}
      {showHazards && hazards?.map(h=>(
        <CircleMarker
          key={'eonet-'+h.eonet_id}
          center={[h.latitude,h.longitude]}
          radius={13}
          pathOptions={{color:'#a855f7',fillColor:'#c084fc',fillOpacity:0.22,weight:2,dashArray:'4 4'}}
          eventHandlers={{click:()=>window.open('https://eonet.gsfc.nasa.gov','_blank','noopener')}}
        >
          <Tooltip direction="top">NASA EONET hazard · {h.title}<br/>{h.category||'Category unavailable'} · {h.event_date||'date unavailable'}<br/>Supporting context only — not a ThermaGuard event</Tooltip>
        </CircleMarker>
      ))}

      {/* OSM Industrial footprint layer */}
      {showIndustrial && events.filter(e=>e.context?.osm_context_available && e.context?.nearby_industrial_count).map(e=>(
        <CircleMarker
          key={'ind-'+e.id}
          center={[e.latitude,e.longitude]}
          radius={18}
          pathOptions={{color:'#f59e0b',fillColor:'#fbbf24',fillOpacity:0.08,weight:1.5,dashArray:'3 5'}}
        >
          <Tooltip direction="top">OSM industrial activity within 5 km of TG event<br/>{e.context.nearby_industrial_count} industrial features · {e.context.landuse_class||'land use unavailable'}</Tooltip>
        </CircleMarker>
      ))}

      {/* Clustered events layer */}
      {!detections && events.map(e=>{
        const isSelected = selected?.id === e.id;
        const isCritical = e.risk?.risk_level === 'Critical';
        const isCrossSensor = e.sensor_summary?.cross_sensor_confirmed === true;
        const mainColor = colorFor(e.risk?.risk_level);
        return (
          <span key={e.id}>
            {isSelected && (
              <CircleMarker
                center={[e.latitude,e.longitude]}
                radius={20}
                pathOptions={{color:mainColor,fillColor:mainColor,fillOpacity:0.2,weight:2,dashArray:'2 3'}}
              />
            )}
            {isCrossSensor && (
              <CircleMarker
                center={[e.latitude,e.longitude]}
                radius={isSelected ? 16 : 12}
                pathOptions={{color:'#38bdf8',fillOpacity:0,weight:1.5,dashArray:'2 2'}}
              />
            )}
            <CircleMarker
              center={[e.latitude,e.longitude]}
              radius={isSelected ? 12 : isCritical ? 10 : 8}
              pathOptions={{color:mainColor,fillColor:mainColor,fillOpacity:isCritical?0.85:0.72,weight:isSelected?3:2}}
              eventHandlers={{click:()=>onSelect(e)}}
            >
              <Tooltip direction="top">
                {e.context?.location?.status==='available' && e.context.location.display_name && (
                  <span><b>{e.context.location.display_name}</b><br/></span>
                )}
                {e.is_demo?'DEMO · ':''}<b>{e.risk?.risk_level||'Risk unavailable'}</b> (Score: {e.risk?.risk_score??'—'})<br/>
                FRP: {typeof e.mean_frp==='number'?e.mean_frp.toFixed(1)+' MW':'FRP unavailable'} · {e.detection_count??'—'} detections<br/>
                Class: {e.classification?.predicted_class?.replace(/_/g,' ')||'Unclassified'}
                {isCrossSensor && <span><br/>✓ Multi-satellite cross-confirmed</span>}
              </Tooltip>
            </CircleMarker>
          </span>
        );
      })}

      {/* Raw FIRMS observations layer */}
      {detections?.map(d=>(
        <CircleMarker
          key={d.id}
          center={[d.latitude,d.longitude]}
          radius={5}
          pathOptions={{color:d.instrument==='MODIS'?'#c084fc':'#38bdf8',fillColor:d.instrument==='MODIS'?'#a855f7':'#0284c7',fillOpacity:0.75,weight:1}}
        >
          <Tooltip direction="top">Raw FIRMS observation{d.is_demo?' · DEMO':''}<br/>{d.source_dataset||'Unknown legacy source'} · {d.satellite} · {d.instrument}<br/>{d.observed_at} · {d.frp} MW</Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
