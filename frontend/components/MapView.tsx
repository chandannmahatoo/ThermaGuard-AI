'use client';
import {MapContainer,TileLayer,CircleMarker,Tooltip,useMap} from 'react-leaflet';
import {useEffect} from 'react';
import type {ThermalEvent} from '../lib/api';
const colors:Record<string,string>={Critical:'#ff5364',High:'#ffae44',Medium:'#f3d05c',Normal:'#38cfaa'};
const colorFor=(level:string|undefined)=>colors[level||'']||'#9aa7ab';
function Focus({selected}:{selected:ThermalEvent|null}){const map=useMap();useEffect(()=>{if(selected)map.flyTo([selected.latitude,selected.longitude],7,{duration:.7});else map.fitBounds([[6,68],[37,98]],{padding:[15,15]})},[selected,map]);return null}
export default function MapView({events,onSelect,selected}:{events:ThermalEvent[];onSelect:(e:ThermalEvent)=>void;selected:ThermalEvent|null}){return <MapContainer center={[23.2,79.4]} zoom={5} minZoom={3} style={{height:'100%',width:'100%'}}><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"/><Focus selected={selected}/>{events.map(e=><CircleMarker key={e.id} center={[e.latitude,e.longitude]} radius={selected?.id===e.id?14:9} pathOptions={{color:colorFor(e.risk?.risk_level),fillColor:colorFor(e.risk?.risk_level),fillOpacity:.7,weight:2}} eventHandlers={{click:()=>onSelect(e)}}><Tooltip>{e.is_demo?'DEMO · ':''}{e.risk?.risk_level||'Risk unavailable'} · {typeof e.mean_frp==='number'?e.mean_frp.toFixed(1)+' MW':'FRP unavailable'} · {e.classification?.predicted_class||'Unclassified'}</Tooltip></CircleMarker>)}</MapContainer>}
