import type {MetadataRoute} from 'next';
export default function manifest():MetadataRoute.Manifest{return {name:'ThermaGuard AI',short_name:'ThermaGuard',description:'Evidence-led thermal monitoring',id:'/',start_url:'/',scope:'/',display:'standalone',background_color:'#f8fafc',theme_color:'#0f766e',icons:[{src:'/icon.svg',sizes:'any',type:'image/svg+xml',purpose:'any'}]};}
