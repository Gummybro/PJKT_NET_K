import type { ReactNode } from "react";
import type { AlertStatus, Severity } from "@/lib/sentinel/types";
import { cn } from "@/lib/utils";

const SEV: Record<Severity, string> = {
  info: "text-muted-foreground border-border",
  low: "text-sev-low border-sev-low/40 bg-sev-low/10",
  medium: "text-sev-medium border-sev-medium/40 bg-sev-medium/10",
  high: "text-sev-high border-sev-high/40 bg-sev-high/10",
  critical: "text-sev-critical border-sev-critical/50 bg-sev-critical/15",
};
export function SevBadge({ s }: { s: Severity }) {
  return <span className={cn("inline-flex rounded border px-1.5 py-0.5 font-mono text-[11px] uppercase", SEV[s])}>{s}</span>;
}

const ST: Record<AlertStatus, string> = {
  open: "text-sev-critical border-sev-critical/40",
  acknowledged: "text-sev-medium border-sev-medium/40",
  resolved: "text-ok border-ok/40",
};
export function StatusBadge({ s }: { s: AlertStatus }) {
  return <span className={cn("inline-flex rounded-full border px-2 py-0.5 text-[11px] capitalize", ST[s])}>{s}</span>;
}

export function PageHeader({ title, sub, children }: { title: string; sub?: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {sub && <p className="mt-1 text-sm text-muted-foreground">{sub}</p>}
      </div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

export function Btn({
  children, onClick, variant = "secondary", disabled, type = "button",
}: { children: ReactNode; onClick?: () => void; variant?: "primary" | "secondary" | "danger" | "ghost"; disabled?: boolean; type?: "button" | "submit" }) {
  const v = {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90",
    secondary: "bg-secondary text-secondary-foreground border border-border hover:bg-accent",
    danger: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
    ghost: "text-muted-foreground hover:text-foreground hover:bg-secondary",
  }[variant];
  return (
    <button type={type} disabled={disabled} onClick={onClick}
      className={cn("inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:opacity-50", v)}>
      {children}
    </button>
  );
}

export function Loading() {
  return <div className="p-10 text-sm text-muted-foreground">Loading local demo data…</div>;
}

export const fmt = (iso: string) => new Date(iso).toLocaleString(undefined, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
