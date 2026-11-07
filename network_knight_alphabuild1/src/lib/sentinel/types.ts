export type Source = string;
export type Severity = "info" | "low" | "medium" | "high" | "critical";
export type AlertStatus = "open" | "acknowledged" | "resolved";
export type Origin = "collector";

export const SOURCES: Source[] = ["auth", "firewall", "endpoint", "web"];
export const SEVERITIES: Severity[] = ["info", "low", "medium", "high", "critical"];

export interface LogEvent {
  id: string;
  ts: string; // ISO
  source: Source;
  severity: Severity;
  ip: string;
  user: string;
  action: string;
  message: string;
  port?: number | undefined;
  origin: Origin;
}

export interface Alert {
  id: string;
  key: string; // dedupe key
  ruleId: string;
  title: string;
  severity: Severity;
  status: AlertStatus;
  createdAt: string;
  updatedAt: string;
  ip: string;
  user: string;
  eventIds: string[];
  reason: string;
  evidence: string[];
  steps: string[];
}

export interface MonitorState {
  version: 1;
  events: LogEvent[];
  alerts: Alert[];
  seq: number;
}
