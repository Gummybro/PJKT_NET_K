import { useSyncExternalStore } from 'react';
import { toast } from 'sonner';
import type { AlertStatus, LogEvent, Severity, Source } from './types';
let state:any={version:1,events:[],alerts:[],seq:0,collectors:[],rules:[],dataset:'live',total:0,services:[],service_activity:[],monitoring_status:'starting',managed:false};
let error='Connecting to FastAPI…',pending=false,connected=false;
let seen:Set<string>|undefined;
let serviceStates:Record<string,string>={};
const listeners=new Set<()=>void>();
const emit=()=>listeners.forEach(fn=>fn());
export async function api(url:string,options:any={}){const r=await fetch(url,{...options,signal:options.signal??AbortSignal.timeout(10000)});const b=await r.json();if(!r.ok)throw Error(typeof b.detail==='string'?b.detail:JSON.stringify(b.detail));return b;}
export async function refresh(){
 if(pending)return;pending=true;
 try{
  const next=await api('/api/state');
  if(!connected){toast.success(seen?'Network Knight reconnected':'Network Knight server is running',{description:'Live component status is shown below.'});}
  if(seen){const fresh=next.alerts.filter((a:any)=>!seen!.has(a.id));if(fresh.length)toast.warning(`${fresh.length} new security alert(s)`,{description:fresh[0].title});}
  for(const service of next.services??[]){
   if(service.id==='backend')continue;
   if(serviceStates[service.id]!==service.state){
    const message=service.name+': '+service.state;
    if(service.state==='running')toast.success(message,{description:service.detail});
    else if(['error','offline','degraded'].includes(service.state))toast.warning(message,{description:service.detail,duration:10000});
    else toast.info(message,{description:service.detail});
   }
  }
  serviceStates=Object.fromEntries((next.services??[]).map((s:any)=>[s.id,s.state]));
  seen=new Set(next.alerts.map((a:any)=>a.id));state={...next,lastReceived:new Date().toISOString()};error='';connected=true;
 }catch(e:any){
  if(connected)toast.error('Network Knight connection lost',{description:'The server may have stopped. Live collection status cannot be confirmed.',duration:10000});
  error='Server offline or unreachable. Run Start-Network-Knight.cmd. '+e.message;connected=false;state={...state};
 }finally{pending=false;emit();}
}
export function getError(){return error;}
export function useMonitor():any{return useSyncExternalStore(cb=>{listeners.add(cb);return()=>listeners.delete(cb)},()=>state,()=>state);}
export const actions={
 async setStatus(id:string,status:AlertStatus){try{await api('/api/alerts/'+id,{method:'PATCH',headers:{'X-Network-Knight':'dashboard','Content-Type':'application/json'},body:JSON.stringify({status})});await refresh();}catch(e:any){toast.error(e.message)}},
 async configure(service:string,enabled:boolean){try{await api('/api/services/'+service,{method:'POST',headers:{'X-Network-Knight':'dashboard','Content-Type':'application/json'},body:JSON.stringify({enabled}),signal:AbortSignal.timeout(25000)});await refresh();}catch(e:any){toast.error('Could not change component',{description:e.message})}},
 async restart(service:string){try{await api('/api/services/'+service+'/restart',{method:'POST',headers:{'X-Network-Knight':'dashboard'},signal:AbortSignal.timeout(25000)});await refresh();}catch(e:any){toast.error('Could not restart component',{description:e.message})}}
};
export interface LogFilter{q:string;severity:Severity|'all';source:Source|'all'}
export function filterEvents(events:LogEvent[],f:LogFilter){const q=f.q.trim().toLowerCase();return events.filter(e=>(f.severity==='all'||e.severity===f.severity)&&(f.source==='all'||e.source===f.source)&&(!q||[e.ip,e.user,e.action,e.message,e.id,(e as any).host,e.source,e.port].some(v=>String(v).toLowerCase().includes(q))))}
if(typeof window!=='undefined'){refresh();setInterval(refresh,2000);}
