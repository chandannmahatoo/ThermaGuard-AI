'use client';
import {MapContainer,TileLayer,Circle,CircleMarker,Polyline,Tooltip,useMap} from 'react-leaflet';
import {Fragment,useState,useEffect,memo} from 'react';
import type {ThermalEvent,RawDetection,EonetHazard} from '../lib/api';

const colors:Record<string,string>={Critical:'#ef4444',High:'#f97316',Medium:'#eab308',Normal:'#10b981'};
const colorFor=(level:string|undefined)=>colors[level||'']||'#94a3b8';

function SelectedHalo({selected}:{selected:ThermalEvent|null}) {
  const map=useMap();
  const [position,setPosition]=useState<{x:number;y:number}|null>(null);
  useEffect(()=>{
    if(!selected){setPosition(null);return;}
    const update=()=>setPosition(map.latLngToContainerPoint([selected.latitude,selected.longitude]));
    update();map.on('move zoom resize',update);
    return ()=>{map.off('move zoom resize',update);};
  },[map,selected]);
  return position ? <span className="selected-map-pulse" aria-hidden="true" style={{left:position.x,top:position.y}}/> : null;
}

function Focus({selected,onClear,onOpenDetail}:{selected:ThermalEvent|null;onClear?:()=>void;onOpenDetail?:()=>void}){
  const map=useMap();
  useEffect(()=>{if(selected)map.flyTo([selected.latitude,selected.longitude],Math.max(map.getZoom(),7),{duration:window.matchMedia('(prefers-reduced-motion: reduce)').matches?0:0.22})},[selected?.id,map]);
  return selected ? <div className="map-selection-actions"><details className="map-selected-mini"><summary>{selected.id.slice(0,22)} · {selected.risk?.risk_level || 'Unavailable'}</summary><p>{selected.detection_count} observations · {selected.mean_frp} MW mean FRP</p></details><button type="button" className="button" onClick={()=>map.flyTo([selected.latitude,selected.longitude],8,{duration:window.matchMedia('(prefers-reduced-motion: reduce)').matches?0:0.8})}>Zoom to selected event</button>{onOpenDetail && <button className="button" onClick={onOpenDetail}>Open event detail</button>}{onClear && <button className="button" onClick={onClear}>Clear selection</button>}</div> : null;
}

export type MapViewProps={
  onClear?:()=>void;
  onOpenDetail?:()=>void;
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

function MapView({onClear,onOpenDetail,events,onSelect,selected,detections,hazards,showHazards,showIndustrial,subscriberLocation,showSubscriberRadius}:MapViewProps){
  const [showSatellite,setShowSatellite] = useState(false);
  return (
    <MapContainer preferCanvas center={[22.5,79.5]} zoom={5} minZoom={3} maxZoom={18} style={{height:'100%',width:'100%'}}>
      <div className="map-status-pill">{detections ? `${detections.length} raw observations` : `${events.length} monitored events`}{selected ? ' · Event selected' : ''}</div><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"/>
      <SelectedHalo selected={selected}/><Focus selected={selected} onClear={onClear} onOpenDetail={onOpenDetail}/><label className="map-satellite-toggle"><input type="checkbox" checked={showSatellite} onChange={e=>setShowSatellite(e.target.checked)}/>Satellite context</label>{showSatellite && events.filter(e=>e.context.satellite_context_available).map(e=><CircleMarker key={`sat-${e.id}`} center={[e.latitude,e.longitude]} radius={16} pathOptions={{color:'#14b8a6',fillOpacity:0,weight:2}}><Tooltip>Satellite context at event · NDVI {e.context.ndvi ?? 'Unavailable'} · {e.context.acquisition_date || 'Acquisition unavailable'}</Tooltip></CircleMarker>)}

      {/* Subscriber notification radius overlay */}
      {showSubscriberRadius && subscriberLocation != null && Number.isFinite(subscriberLocation.latitude) && Number.isFinite(subscriberLocation.longitude) && (
        <Circle
          center={[subscriberLocation.latitude, subscriberLocation.longitude]}
          radius={subscriberLocation.radiusKm * 1000}
          pathOptions={{color:'#38bdf8',fillColor:'#0284c7',fillOpacity:0.12,weight:2,dashArray:'6 6'}}
        >
          <Tooltip direction="top">Subscriber Alert Zone<br/>Radius: {subscriberLocation.radiusKm} km around home coordinates</Tooltip>
        </Circle>
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
          <Tooltip direction="top">OSM industrial activity near this event (event position; not a facility location)<br/>{e.context.nearby_industrial_count} industrial features · {e.context.landuse_class||'land use unavailable'}</Tooltip>
        </CircleMarker>
      ))}

      {/* Clustered events layer */}
      {!detections && events.map(e=>{
        const isSelected = selected?.id === e.id;
        const isCritical = e.risk?.risk_level === 'Critical';
        const isCrossSensor = e.sensor_summary?.cross_sensor_confirmed === true;
        const mainColor = colorFor(e.risk?.risk_level);
        return (
          <Fragment key={e.id}>
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
              radius={isSelected ? 12 : isCritical ? 10 : e.risk?.risk_level === 'High' ? 9 : e.risk?.risk_level === 'Medium' ? 7 : 5}
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
          </Fragment>
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

export default memo(MapView);
