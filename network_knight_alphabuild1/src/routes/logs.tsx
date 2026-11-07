import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Download, Search } from "lucide-react";
import { filterEvents, useMonitor, type LogFilter } from "@/lib/sentinel/store";
import { SEVERITIES, SOURCES } from "@/lib/sentinel/types";
import { download, toCsv } from "@/lib/sentinel/csv";
import { Btn, Loading, PageHeader, SevBadge, fmt } from "@/components/sentinel/bits";

export const Route = createFileRoute("/logs")({
  head: () => ({
    meta: [
      { title: "Event Logs — Network Knight" },
      { name: "description", content: "Search and filter collected local security event logs by severity and source, and export to CSV." },
      { property: "og:title", content: "Event Logs — Network Knight" },
      { property: "og:description", content: "Search, filter and export collected local security logs." },
    ],
  }),
  component: Logs,
});

const PAGE = 50;

function Logs() {
  const d = useMonitor();
  const [f, setF] = useState<LogFilter>({ q: "", severity: "all", source: "all" });
  const [limit, setLimit] = useState(PAGE);
  const rows = useMemo(() => (d ? filterEvents(d.events, f) : []), [d, f]);
  if (!d) return <Loading />;
  const sel = "rounded-md border border-input bg-card px-3 py-2 text-sm";
  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Event Logs" sub={`${rows.length} of ${d.events.length} loaded events match`}>
        <Btn onClick={() => download(`network-knight-logs-${new Date().toISOString().slice(0, 10)}.csv`, toCsv(rows))} disabled={!rows.length}>
          <Download className="h-4 w-4" /> Export filtered CSV
        </Btn>
      </PageHeader>
      <div className="panel mb-4 flex flex-wrap gap-2 p-3">
        <label className="relative min-w-56 flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input aria-label="Search logs" placeholder="Search IP, user, action, message, port…" value={f.q}
            onChange={(e) => { setF({ ...f, q: e.target.value }); setLimit(PAGE); }}
            className={`${sel} w-full pl-9`} />
        </label>
        <select aria-label="Severity filter" className={sel} value={f.severity} onChange={(e) => setF({ ...f, severity: e.target.value as LogFilter["severity"] })}>
          <option value="all">All severities</option>
          {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select aria-label="Source filter" className={sel} value={f.source} onChange={(e) => setF({ ...f, source: e.target.value as LogFilter["source"] })}>
          <option value="all">All sources</option>
          {[...new Set<string>(d.events.map((e:any)=>e.source))].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        {(f.q || f.severity !== "all" || f.source !== "all") && <Btn variant="ghost" onClick={() => setF({ q: "", severity: "all", source: "all" })}>Clear</Btn>}
      </div>
      <div className="panel overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-border text-left text-xs uppercase tracking-wider text-muted-foreground">
            <tr>{["Time", "Severity", "Source", "IP", "User", "Action", "Port", "Message", "Origin"].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.slice(0, limit).map((e) => (
              <tr key={e.id} className="hover:bg-secondary/50" data-testid="log-row">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-muted-foreground">{fmt(e.ts)}</td>
                <td className="px-3 py-2"><SevBadge s={e.severity} /></td>
                <td className="px-3 py-2 capitalize">{e.source}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.ip}</td>
                <td className="px-3 py-2">{e.user}</td>
                <td className="px-3 py-2 font-mono text-xs text-primary">{e.action}</td>
                <td className="px-3 py-2 font-mono text-xs">{e.port ?? ""}</td>
                <td className="max-w-md truncate px-3 py-2 text-muted-foreground" title={e.message}>{e.message}</td>
                <td className="px-3 py-2 text-xs text-muted-foreground">{e.origin}</td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={9} className="p-8 text-center text-muted-foreground">No events match these filters.</td></tr>}
          </tbody>
        </table>
      </div>
      {rows.length > limit && <div className="mt-3 text-center"><Btn onClick={() => setLimit(limit + PAGE)}>Show more ({rows.length - limit} remaining)</Btn></div>}
    </div>
  );
}
