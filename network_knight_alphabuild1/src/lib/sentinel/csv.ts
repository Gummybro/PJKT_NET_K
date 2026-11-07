import { SEVERITIES, SOURCES, type LogEvent, type Severity, type Source } from "./types";

export const MAX_FILE_BYTES = 1024 * 1024;
export const MAX_ROWS = 2000;
export const REQUIRED_HEADERS = ["timestamp", "source", "severity", "ip", "user", "action", "message"];
export const OPTIONAL_HEADERS = ["port"];

export const SAMPLE_CSV = `timestamp,source,severity,ip,user,action,message,port
2026-10-22T09:00:00Z,auth,medium,203.0.113.45,alice,login_failed,Failed password for alice,
2026-10-22T09:00:30Z,auth,medium,203.0.113.45,alice,login_failed,Failed password for alice,
2026-10-22T09:01:00Z,auth,medium,203.0.113.45,alice,login_failed,Failed password for alice,
2026-10-22T09:01:30Z,auth,medium,203.0.113.45,alice,login_failed,Failed password for alice,
2026-10-22T09:02:00Z,auth,medium,203.0.113.45,alice,login_failed,Failed password for alice,
2026-10-22T09:05:00Z,firewall,low,192.0.2.10,-,connection_allowed,Outbound HTTPS allowed,443
2026-10-22T09:06:00Z,web,low,192.0.2.14,bob,http_request,GET /reports 200,
`;

export function parseCsvText(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (ch === '"') q = false;
      else cell += ch;
    } else if (ch === '"') q = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); cell = "";
      if (row.some((c) => c.trim() !== "")) rows.push(row);
      row = [];
    } else cell += ch;
  }
  row.push(cell);
  if (row.some((c) => c.trim() !== "")) rows.push(row);
  return rows;
}

const IPV4 = /^(25[0-5]|2[0-4]\d|1?\d?\d)(\.(25[0-5]|2[0-4]\d|1?\d?\d)){3}$/;

export interface CsvResult {
  ok: boolean;
  events: Omit<LogEvent, "id">[];
  errors: string[];
}

export function validateCsv(text: string, sizeBytes = text.length): CsvResult {
  const fail = (errors: string[]): CsvResult => ({ ok: false, events: [], errors });
  if (sizeBytes > MAX_FILE_BYTES) return fail([`File is too large (max ${MAX_FILE_BYTES / 1024} KB).`]);
  const rows = parseCsvText(text.replace(/^\uFEFF/, ""));
  if (rows.length === 0) return fail(["File is empty."]);
  const headers = rows[0]!.map((h) => h.trim().toLowerCase());
  const missing = REQUIRED_HEADERS.filter((h) => !headers.includes(h));
  if (missing.length) return fail([`Missing required header(s): ${missing.join(", ")}.`]);
  const unknown = headers.filter((h) => ![...REQUIRED_HEADERS, ...OPTIONAL_HEADERS].includes(h));
  if (unknown.length) return fail([`Unknown header(s): ${unknown.join(", ")}.`]);
  const data = rows.slice(1);
  if (data.length === 0) return fail(["No data rows found."]);
  if (data.length > MAX_ROWS) return fail([`Too many rows: ${data.length} (max ${MAX_ROWS}).`]);
  const errors: string[] = [];
  const events: Omit<LogEvent, "id">[] = [];
  const idx = (h: string) => headers.indexOf(h);
  data.forEach((r, i) => {
    const line = i + 2;
    const get = (h: string) => (idx(h) >= 0 ? (r[idx(h)] ?? "").trim() : "");
    const errs: string[] = [];
    const ts = get("timestamp");
    const d = new Date(ts);
    if (!ts || isNaN(d.getTime())) errs.push(`invalid timestamp "${ts}"`);
    const source = get("source").toLowerCase();
    if (!SOURCES.includes(source as Source)) errs.push(`source must be one of ${SOURCES.join("/")}`);
    const severity = get("severity").toLowerCase();
    if (!SEVERITIES.includes(severity as Severity)) errs.push(`severity must be one of ${SEVERITIES.join("/")}`);
    const ip = get("ip");
    if (!IPV4.test(ip)) errs.push(`invalid IPv4 "${ip}"`);
    const action = get("action");
    if (!/^[a-z0-9_]{1,40}$/i.test(action)) errs.push("action must be 1-40 letters/digits/underscores");
    const message = get("message");
    if (message.length > 500) errs.push("message longer than 500 characters");
    const portRaw = get("port");
    let port: number | undefined;
    if (portRaw) {
      port = Number(portRaw);
      if (!Number.isInteger(port) || port < 0 || port > 65535) errs.push(`invalid port "${portRaw}"`);
    }
    if (errs.length) errors.push(`Row ${line}: ${errs.join("; ")}`);
    else
      events.push({
        ts: d.toISOString(),
        source: source as Source,
        severity: severity as Severity,
        ip,
        user: get("user").slice(0, 64) || "-",
        action: action.toLowerCase(),
        message,
        port,
        origin: "import",
      });
  });
  if (errors.length) return fail(errors);
  return { ok: true, events, errors: [] };
}

/** Neutralize spreadsheet formula injection and quote cells. */
export function safeCell(v: unknown): string {
  let s = v == null ? "" : String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
  return `"${s.replace(/"/g, '""')}"`;
}

export function toCsv(events: LogEvent[]): string {
  const head = ["timestamp", "source", "severity", "ip", "user", "action", "message", "port", "origin"];
  const lines = events.map((e) =>
    [e.ts, e.source, e.severity, e.ip, e.user, e.action, e.message, e.port ?? "", e.origin].map(safeCell).join(","),
  );
  return [head.join(","), ...lines].join("\r\n");
}

export function download(name: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
