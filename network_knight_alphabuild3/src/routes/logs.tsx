import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { api, useMonitor } from "@/lib/sentinel/store";
import { openSession, tabId } from "@/lib/sentinel/tab-session";
import { SEVERITIES, type LogEvent } from "@/lib/sentinel/types";
import { download, toCsv } from "@/lib/sentinel/csv";
import { Btn, PageHeader, SevBadge, fmt } from "@/components/sentinel/bits";

export const Route = createFileRoute("/logs")({component: Logs});
type Page = {events: LogEvent[]; total: number; more: boolean};
function guidance(event: LogEvent) {
  if (event.action === 'workstation_locked') return 'Windows recorded a workstation lock. Compare its time with when the user locked the screen.';
  if (event.action === 'defender_disabled') return 'Check Virus & threat protection in Windows Security and compare the current setting with the event time.';
  if (event.action === 'login_failed') return 'Review the account and source IP. Look for repeated failures around this time.';
  return 'Compare the event time, provider and host with Windows Event Viewer. Check Data Sources if expected records are missing.';
}
function Logs() {
  const monitor = useMonitor();
  const [scope, setScope] = useState('session');
  const [q, search] = useState('');
  const [severity, filter] = useState('');
  const [source, selectSource] = useState('');
  const [pages, paginate] = useState<number[]>([0]);
  const [data, show] = useState<Page | null>(null);
  const [error, report] = useState('');
  const [busy, working] = useState(false);
  const [revision, refresh] = useState(0);
  const cursor = pages[pages.length-1];
  const query = new URLSearchParams({session:scope==='session'?tabId:'',q,severity,source});
  const url = '/api/log-page?' + query;
  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    show(null); report('');
    async function poll() {
      try {
        if(scope==='session') await openSession();
        const page = await api(url+'&before='+cursor);
        if(live) {show(page); report('');}
      } catch(e) {if(live) report(String(e));}
      if(live) timer=setTimeout(poll,2000);
    }
    void poll();
    return () => {live=false;clearTimeout(timer);};
  },[url,cursor,revision,scope]);
  const [actionError, feedback] = useState('');
  async function clear() {
    if(!window.confirm('Clear this session view? All events and alerts stay in history. Windows administrator approval is required.')) return;
    working(true);feedback('');
    try {
      await api('/api/log-sessions/'+tabId+'/clear',{method:'POST',headers:{'X-Network-Knight':'dashboard'},signal:AbortSignal.timeout(120000)});
      paginate([0]);refresh(v=>v+1);
    } catch(e) {feedback(String(e));} finally {working(false);}
  }
  async function exportRows() {
    working(true);feedback('');
    try {
      const rows: LogEvent[]=[];
      let before=0;
      while(true) {
        const page: Page=await api(url+'&before='+before);
        rows.push(...page.events);
        if(!page.more) break;
        before=Number(page.events.at(-1)?.id);
      }
      download('network-knight-logs.csv',toCsv(rows));
    } catch(e) {feedback(String(e));} finally {working(false);}
  }
  return <div className="mx-auto max-w-7xl"><PageHeader title="Event logs" sub="Inspect a Windows event or follow activity as it arrives."/>
    <div className="panel mb-4 space-y-3 p-4">
      <div className="flex flex-wrap gap-2">{['session','all'].map(s=><button key={s} aria-pressed={scope===s} className={'rounded px-4 py-2 '+(scope===s?'bg-primary text-black':'bg-muted')} onClick={()=>{setScope(s);paginate([0]);}}>{s==='session'?'This session':'All logs'}</button>)}</div>
      <p>{scope==='session'?'Events collected since this browser tab opened or was cleared.':'Search the complete saved event history.'}</p>
      <div className="flex flex-wrap gap-2">
        <input className="flex-1 rounded bg-muted p-2" aria-label="Search events" placeholder="Search message, account, host or action" value={q} onChange={e=>{search(e.target.value);paginate([0]);}}/>
        <select className="rounded bg-muted p-2" aria-label="Severity" value={severity} onChange={e=>{filter(e.target.value);paginate([0]);}}><option value="">All severities</option>{SEVERITIES.map(s=><option key={s}>{s}</option>)}</select>
        <select className="rounded bg-muted p-2" aria-label="Source" value={source} onChange={e=>{selectSource(e.target.value);paginate([0]);}}><option value="">All sources</option>{Array.from(new Set<string>(monitor.events.map((e:LogEvent)=>e.source))).map(s=><option key={s}>{s}</option>)}</select>
      </div>
      <div className="flex flex-wrap items-center gap-3"><span>{data ? data.total+' matching events':'Loading…'}</span><Btn disabled={busy||!data?.total} onClick={exportRows}>Export filtered CSV</Btn>{scope==='session'&&<Btn disabled={busy||!data} onClick={clear}>Clear session · Admin</Btn>}</div>
      {(error||actionError)&&<p role="alert">{error||actionError}</p>}
    </div>
    <div className="panel divide-y divide-border">{data?.events.map(e=><details key={e.id} className="p-3"><summary className="cursor-pointer"><SevBadge s={e.severity}/> <strong>{e.action.replaceAll('_',' ')}</strong> · {fmt(e.ts)} <span className="text-muted-foreground">{e.source}</span></summary><p className="my-2 whitespace-pre-wrap break-words">{e.message}</p><p>Event #{e.id} · Account {e.user} · IP {e.ip}</p><p className="mt-2 text-primary">Investigation tip</p><p>{guidance(e)}</p><pre className="mt-2 overflow-auto text-xs">{JSON.stringify((e as LogEvent & {details:unknown}).details,null,2)}</pre></details>)}
    {data&&!data.total&&<p className="p-6">{q||severity||source?'No matching events. Try another filter.':scope==='session'?'Waiting for the next real event. Earlier events are in All logs.':'No collected events. Check collector health in Data Sources.'}</p>}</div>
    <div className="mt-3 flex gap-2"><Btn disabled={pages.length===1} onClick={()=>paginate(p=>p.slice(0,-1))}>Newer</Btn><Btn disabled={!data?.more} onClick={()=>paginate(p=>[...p,Number(data?.events.at(-1)?.id)])}>Older</Btn></div></div>;
}
