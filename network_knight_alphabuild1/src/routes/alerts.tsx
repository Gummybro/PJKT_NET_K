import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { actions, useMonitor } from "@/lib/sentinel/store";
import type { AlertStatus } from "@/lib/sentinel/types";
import { Btn, Loading, PageHeader, SevBadge, StatusBadge, fmt } from "@/components/sentinel/bits";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/alerts")({
  validateSearch: (s: Record<string, unknown>): { id?: string } => (typeof s["id"] === "string" ? { id: s["id"] } : {}),
  head: () => ({
    meta: [
      { title: "Alerts — Network Knight" },
      { name: "description", content: "Triage rule-based alerts with evidence, rule reasons and suggested investigation steps." },
      { property: "og:title", content: "Alerts — Network Knight" },
      { property: "og:description", content: "Triage rule-based alerts with evidence and investigation steps." },
    ],
  }),
  component: Alerts,
});

function Alerts() {
  const d = useMonitor();
  const { id } = Route.useSearch();
  const navigate = useNavigate({ from: "/alerts" });
  const [status, setStatus] = useState<AlertStatus | "all">("all");
  if (!d) return <Loading />;
  const list = [...d.alerts].sort((a, b) => b.createdAt.localeCompare(a.createdAt)).filter((a) => status === "all" || a.status === status);
  const sel = d.alerts.find((a) => a.id === id) ?? list[0];
  const evs = sel ? d.events.filter((e) => sel.eventIds.includes(e.id)).sort((a, b) => a.ts.localeCompare(b.ts)) : [];

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader title="Alerts" sub="Server-generated rules with persisted evidence and status. Burst matches merge for 60 seconds.">
        {(["all", "open", "acknowledged", "resolved"] as const).map((s) => (
          <Btn key={s} variant={status === s ? "primary" : "secondary"} onClick={() => setStatus(s)}>
            <span className="capitalize">{s}</span> <span className="font-mono text-xs opacity-70">{s === "all" ? d.alerts.length : d.alerts.filter((a) => a.status === s).length}</span>
          </Btn>
        ))}
      </PageHeader>
      <div className="grid gap-4 lg:grid-cols-[22rem_1fr]">
        <ul className="panel max-h-[70vh] divide-y divide-border overflow-y-auto">
          {list.map((a) => (
            <li key={a.id}>
              <button onClick={() => navigate({ search: { id: a.id } })}
                className={cn("block w-full px-4 py-3 text-left hover:bg-secondary/60", sel?.id === a.id && "bg-accent shadow-[inset_2px_0_0_var(--primary)]")}>
                <div className="flex items-center gap-2"><SevBadge s={a.severity} /><span className="font-mono text-[11px] text-muted-foreground">{a.id}</span><span className="ml-auto"><StatusBadge s={a.status} /></span></div>
                <div className="mt-1 text-sm">{a.title}</div>
                <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">{a.dataset} · {a.ruleId} · {a.eventIds.length} events · {fmt(a.createdAt)}</div>
              </button>
            </li>
          ))}
          {!list.length && <li className="p-6 text-sm text-muted-foreground">No alerts in this view.</li>}
        </ul>

        {sel ? (
          <section className="panel min-w-0 p-5" aria-label="Alert details">
            <div className="flex flex-wrap items-center gap-2">
              <SevBadge s={sel.severity} /><StatusBadge s={sel.status} />
              <span className="font-mono text-xs text-muted-foreground">{sel.id} · rule {sel.ruleId}</span>
            </div>
            <h2 className="mt-2 text-xl font-semibold">{sel.title}</h2>
            <div className="mt-1 text-xs text-muted-foreground">Created {fmt(sel.createdAt)} · Updated {fmt(sel.updatedAt)} · IP <span className="font-mono">{sel.ip}</span> · User {sel.user}</div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Btn disabled={sel.status !== "open"} onClick={() => actions.setStatus(sel.id, "acknowledged")}>Acknowledge</Btn>
              <Btn variant="primary" disabled={sel.status === "resolved"} onClick={() => actions.setStatus(sel.id, "resolved")}>Resolve</Btn>
              {sel.status !== "open" && <Btn variant="ghost" onClick={() => actions.setStatus(sel.id, "open")}>Reopen</Btn>}
            </div>
            <h3 className="mt-6 text-xs uppercase tracking-wider text-muted-foreground">Rule reason</h3>
            <p className="mt-1 rounded-md border border-border bg-muted/40 p-3 text-sm">{sel.reason}</p>
            <h3 className="mt-6 text-xs uppercase tracking-wider text-muted-foreground">Evidence · {evs.length} linked events</h3>
            <div className="mt-1 overflow-x-auto rounded-md border border-border">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-muted-foreground"><tr>{["Event ID", "Time", "Action", "IP", "User", "Port", "Message"].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr></thead>
                <tbody className="divide-y divide-border">
                  {evs.map((e) => (
                    <tr key={e.id}>
                      <td className="whitespace-nowrap px-3 py-1.5 font-mono text-xs text-primary">{e.id}</td>
                      <td className="whitespace-nowrap px-3 py-1.5 font-mono text-xs">{fmt(e.ts)}</td>
                      <td className="px-3 py-1.5 font-mono text-xs">{e.action}</td>
                      <td className="px-3 py-1.5 font-mono text-xs">{e.ip}</td>
                      <td className="px-3 py-1.5">{e.user}</td>
                      <td className="px-3 py-1.5 font-mono text-xs">{e.port ?? ""}</td>
                      <td className="px-3 py-1.5 text-muted-foreground">{e.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h3 className="mt-6 text-xs uppercase tracking-wider text-muted-foreground">Suggested investigation steps</h3>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">{sel.steps.map((s) => <li key={s}>{s}</li>)}</ol>
            <p className="mt-6 text-xs text-muted-foreground">Static investigation guidance. A rule match alone does not prove compromise.</p>
          </section>
        ) : <div className="panel p-8 text-sm text-muted-foreground">Select an alert.</div>}
      </div>
    </div>
  );
}
