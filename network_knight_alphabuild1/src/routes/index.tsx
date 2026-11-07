import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMemo } from "react";
import { useMonitor } from "@/lib/sentinel/store";
import { SEVERITIES, SOURCES } from "@/lib/sentinel/types";
import { Loading, PageHeader, SevBadge, StatusBadge, fmt, Btn } from "@/components/sentinel/bits";


export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Overview — Network Knight" },
      { name: "description", content: "SOC overview of collected log volume, severities and open alerts in the Network Knight local monitor." },
      { property: "og:title", content: "Overview — Network Knight" },
      { property: "og:description", content: "SOC overview of collected security events and rule-based alerts." },
    ],
  }),
  component: Overview,
});

function Overview() {
  const d = useMonitor();
  const navigate = useNavigate();
  const stats = useMemo(() => {
    if (!d) return null;
    const now = Date.now();
    const last24 = d.events.filter((e) => now - new Date(e.ts).getTime() < 864e5);
    const hours = Array.from({ length: 24 }, (_, i) => {
      const end = now - (23 - i) * 36e5;
      return d.events.filter((e) => { const t = new Date(e.ts).getTime(); return t <= end && t > end - 36e5; }).length;
    });
    const sev = SEVERITIES.map((s) => ({ s, n: d.events.filter((e) => e.severity === s).length }));
    const src = [...new Set<string>(d.events.map((e:any)=>e.source))].map((s) => ({ s, n: d.events.filter((e) => e.source === s).length }));
    const ipCounts = new Map<string, number>();
    d.events.filter((e) => e.action.includes("fail") || e.action.includes("denied")).forEach((e) => ipCounts.set(e.ip, (ipCounts.get(e.ip) ?? 0) + 1));
    const topIps = [...ipCounts].sort((a, b) => b[1] - a[1]).slice(0, 5);
    return {
      total: d.events.length, last24: last24.length,
      open: d.alerts.filter((a) => a.status === "open").length,
      ack: d.alerts.filter((a) => a.status === "acknowledged").length,
      resolved: d.alerts.filter((a) => a.status === "resolved").length,
      highCrit: d.events.filter((e) => e.severity === "high" || e.severity === "critical").length,
      hours, sev, src, topIps,
    };
  }, [d]);
  if (!d || !stats) return <Loading />;
  const maxH = Math.max(1, ...stats.hours);
  const maxSev = Math.max(1, ...stats.sev.map((x) => x.n));
  const maxSrc = Math.max(1, ...stats.src.map((x) => x.n));
  const protection = d.collectors.find((c:any)=>c.id.startsWith('protection:'));
  const freshProtection = protection && Date.now()-Date.parse(protection.last_seen)<30000;
  const recent = [...d.alerts].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).slice(0, 5);

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Security Overview" sub="Live protection observations and Windows Event Logs from this computer." />
      <section className="panel mb-4 p-4" aria-label="Live laptop protection status"><h2 className="mb-3 font-semibold">Live laptop protection</h2><p className="mb-3 text-xs text-muted-foreground">Actual device status from the local protection monitor. Read-only checks; no settings are changed. Third-party antivirus is not assessed.</p><div className="grid grid-cols-2 gap-3 lg:grid-cols-4">{[['defender','Microsoft Defender'],['firewall:Public','Firewall · Public'],['firewall:Private','Firewall · Private'],['firewall:Domain','Firewall · Domain']].map(([key,label])=>{const value=freshProtection?protection.checks?.[key]:undefined;return <div key={key} className="rounded border border-border p-3"><p className="text-xs text-muted-foreground">{label}</p><p className={'mt-1 font-mono font-semibold '+(value===true?'text-primary':value===false?'text-sev-critical':'text-muted-foreground')}>{value===true?'ON':value===false?'OFF':'UNAVAILABLE'}</p></div>})}</div><p className="mt-3 text-xs text-muted-foreground">{freshProtection?protection.detail:'Protection monitor not connected or heartbeat stale. Start the app using Start-Network-Knight.cmd.'}</p></section>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {[
          ["Total events", stats.total, "text-foreground"],
          ["Events (24h)", stats.last24, "text-primary"],
          ["High / critical events", stats.highCrit, "text-sev-high"],
          ["Open alerts", stats.open, "text-sev-critical"],
          ["Resolved alerts", stats.resolved, "text-ok"],
        ].map(([l, v, c]) => (
          <div key={l as string} className="panel p-4">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">{l}</div>
            <div className={`mt-2 font-mono text-3xl font-semibold ${c}`}>{v}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="panel p-4 lg:col-span-2">
          <div className="mb-3 text-sm font-medium">Event volume · last 24 hours (per hour)</div>
          <div className="flex h-40 items-end gap-1">
            {stats.hours.map((h, i) => (
              <div key={i} title={`${h} events`} className="flex-1 rounded-t bg-primary/70 hover:bg-primary" style={{ height: `${(h / maxH) * 100}%`, minHeight: 2 }} />
            ))}
          </div>
          <div className="mt-1 flex justify-between font-mono text-[10px] text-muted-foreground"><span>-24h</span><span>now</span></div>
        </div>
        <div className="panel p-4">
          <div className="mb-3 text-sm font-medium">Events by severity</div>
          {stats.sev.map(({ s, n }) => (
            <div key={s} className="mb-2 flex items-center gap-2 text-sm">
              <div className="w-20"><SevBadge s={s} /></div>
              <div className="h-2 flex-1 rounded bg-muted"><div className={`h-2 rounded bg-sev-${s}`} style={{ width: `${(n / maxSev) * 100}%` }} /></div>
              <span className="w-10 text-right font-mono text-xs">{n}</span>
            </div>
          ))}
          <div className="mb-3 mt-5 text-sm font-medium">Events by source</div>
          {stats.src.map(({ s, n }) => (
            <div key={s} className="mb-2 flex items-center gap-2 text-sm">
              <span className="w-20 font-mono text-xs capitalize text-muted-foreground">{s}</span>
              <div className="h-2 flex-1 rounded bg-muted"><div className="h-2 rounded bg-primary" style={{ width: `${(n / maxSrc) * 100}%` }} /></div>
              <span className="w-10 text-right font-mono text-xs">{n}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="panel p-4 lg:col-span-2">
          <div className="mb-3 flex items-center text-sm font-medium">Recent alerts <Link to="/alerts" className="ml-auto text-xs text-primary">View all</Link></div>
          {recent.length === 0 && <p className="text-sm text-muted-foreground">No security alerts have been detected in the collected local events.</p>}
          <ul className="divide-y divide-border">
            {recent.map((a) => (
              <li key={a.id}>
                <Link to="/alerts" search={{ id: a.id }} className="flex flex-wrap items-center gap-3 py-2 text-sm hover:text-primary">
                  <SevBadge s={a.severity} /><span className="font-mono text-xs text-muted-foreground">{a.ruleId}</span>
                  <span className="min-w-0 flex-1 truncate">{a.title}</span><StatusBadge s={a.status} />
                  <span className="font-mono text-xs text-muted-foreground">{fmt(a.createdAt)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div className="panel p-4">
          <div className="mb-3 text-sm font-medium">Top IPs (failed / denied)</div>
          {stats.topIps.map(([ip, n]) => (
            <div key={ip} className="flex justify-between py-1 font-mono text-sm"><span>{ip}</span><span className="text-muted-foreground">{n}</span></div>
          ))}
          <p className="mt-4 text-xs text-muted-foreground">Only real collector records are shown. Check Data Sources for channel permissions, errors and fresh heartbeats.</p>
        </div>
      </div>
    </div>
  );
}
