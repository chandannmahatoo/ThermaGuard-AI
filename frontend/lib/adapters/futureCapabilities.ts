export type FutureCapability={id:string;title:string;available:false;reason:string;endpoint:string;method:'GET'|'PUT'|'POST';fields:string[]};
const unsupported=(id:string,title:string,method:FutureCapability['method'],endpoint:string,fields:string[]):FutureCapability=>({id,title,available:false,reason:'Not yet supported by backend',method,endpoint,fields});
/** Proposed contracts only. No network calls or simulated mutation success. */
export const futureCapabilities:FutureCapability[]=[
 unsupported('training-reference','Training geographic and sensor reference','GET','/api/v1/model/training-reference',['regions','sensor_counts','class_counts','feature_missingness','reference_version']),
 unsupported('similarity','Model-based similar events','GET','/api/v1/events/{id}/similar',['method','model_version','event_ids','scores']),
 unsupported('review','Save review','PUT','/api/v1/events/{id}/review',['label','reviewer','source_reference','notes','evidence_version']),
 unsupported('diff','Evidence changes','GET','/api/v1/events/{id}/evidence-diff',['before_version','after_version','changes']),
 unsupported('lifecycle','Update incident lifecycle','PUT','/api/v1/events/{id}/lifecycle',['state','owner','notes','expected_version']),
 unsupported('response','Response checklist and escalation','PUT','/api/v1/events/{id}/response',['owner','checklist','escalation_state','resolution']),
 unsupported('facilities','Facility history','GET','/api/v1/facilities/{id}/events',['facility','geometry','type','distance_m','events']),
 unsupported('watchlists','Sync watchlist across devices','PUT','/api/v1/auth/watchlist',['event_ids','facility_ids','regions']),
 unsupported('experiments','Experiment registry and model history','GET','/api/v1/model/versions',['versions','experiments','metrics','feature_version']),
 unsupported('rollback','Rollback model','POST','/api/v1/model/rollback',['target_version','reason','expected_current_version']),
 unsupported('shadow','Shadow model comparison','GET','/api/v1/model/shadow-results',['event_id','model_versions','predictions']),
 unsupported('drift','Statistical drift baseline','GET','/api/v1/model/drift',['reference_window','current_window','statistic','threshold','sample_counts']),
 unsupported('explanation','Local feature attribution / SHAP','GET','/api/v1/events/{id}/explanation',['model_version','method','feature_attributions','baseline']),
 unsupported('audit','Versioned event audit','GET','/api/v1/events/{id}/audit',['timestamp','actor','action','before','after']),
 unsupported('consensus','Reviewer disagreement and consensus','GET','/api/v1/events/{id}/reviews',['reviews','disagreement','senior_review','consensus']),
 unsupported('outcome','Verified outcome feedback','POST','/api/v1/events/{id}/outcome',['outcome','source_reference','reviewer','verified_at']),
];
