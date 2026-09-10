export async function api<T>(path:string, token:string, body?:unknown):Promise<T>{
 const response=await fetch('/api/v1'+path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Request failed. Check your input.');return data as T;
}
export type ThermalEvent={id:string;latitude:number;longitude:number;is_demo:boolean;start_time:string;last_seen_time:string;duration_hours:number;detection_count:number;mean_frp:number;max_frp:number;mean_brightness:number;persistence_days:number;classification:{predicted_class:string|null;classification_confidence:number|null;reason?:string};context:Record<string,unknown>&{satellite_context_available?:boolean;ndvi?:number|null;acquisition_date?:string;reason?:string};risk:{risk_score:number;risk_level:string;risk_factors:Record<string,number>;missing_context:string[];abnormality:{baseline_available:boolean;abnormality_status:string}}};
export type User={email:string;role:string};
export type ModelStatus={training_ready:boolean;model_available:boolean;reason:string;eligible_labeled_rows:number;model_version:string|null};
export type Alert={id:number;event_id:string;risk_level:string;status:string;notification_status:string;is_demo:boolean};
export type FirmsStatus={available:boolean;configured:boolean;mode:string;reason:string|null;last_success:string|null};
export type TrendPoint={date:string;events:number;mean_risk:number};
