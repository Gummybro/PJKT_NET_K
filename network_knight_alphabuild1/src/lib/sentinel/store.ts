import { useSyncExternalStore } from 'react';
import { toast } from 'sonner';
import type { AlertStatus, LogEvent, Severity, Source } from './types';
let state:any={version:1,events:[],alerts:[],seq:0,collectors:[],rules:[],dataset:'live',total:0};
let error='Connecting to FastAPI…',pending=false;
let seen:Set<string>|undefined;
const listeners=new Set<()=>void>();
const emit=()=>listeners.forEach(fn=>fn());
export async function api(url:string,options:any={}){const r=await fetch(url,options);const b=await r.json();if(!r.ok)throw Error(typeof b.detail==='string'?b.detail:JSON.stringify(b.detail));return b;}
export async function refresh(){if(pending)return;pending=true;try{const next=await api('/api/state');if(seen){const fresh=next.alerts.filter((a:any)=>!seen!.has(a.id));if(fresh.length)toast.warning(`${fresh.length} new security alert(s)`,{description:fresh[0].title});}seen=new Set(next.alerts.map((a:any)=>a.id));state=next;error='';}catch(e:any){error=e.message;state={...state};}finally{pending=false;emit();}}
export function getError(){return error;}
export function useMonitor():any{return useSyncExternalStore(cb=>{listeners.add(cb);return()=>listeners.delete(cb)},()=>state,()=>state);}
export const actions={async setStatus(id:string,status:AlertStatus){try{await api('/api/alerts/'+id,{method:'PATCH',headers:{'X-Network-Knight':'dashboard','Content-Type':'application/json'},body:JSON.stringify({status})});await refresh();}catch(e:any){toast.error(e.message)}}};
export interface LogFilter{q:string;severity:Severity|'all';source:Source|'all'}
export function filterEvents(events:LogEvent[],f:LogFilter){const q=f.q.trim().toLowerCase();return events.filter(e=>(f.severity==='all'||e.severity===f.severity)&&(f.source==='all'||e.source===f.source)&&(!q||[e.ip,e.user,e.action,e.message,e.id,(e as any).host,e.source,e.port].some(v=>String(v).toLowerCase().includes(q))))}
if(typeof window!=='undefined'){refresh();setInterval(refresh,2000);}
