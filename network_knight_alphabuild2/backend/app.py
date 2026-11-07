"""Network Knight: local FastAPI ingestion, SQLite evidence and deterministic rules."""
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from backend.service_control import Preferences, collector_status, instance_id, overall_status

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 1024 * 1024
from backend.detection import RULES, detect



def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def timestamp(value):
    try:
        # Windows/.NET emits seven fractional digits; Python 3.10 accepts at most six.
        raw = re.sub(r'(\.\d{6})\d+', r'\1', str(value).replace("Z", "+00:00"))
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            raise ValueError()
        dt = dt.astimezone(timezone.utc)
        if dt > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError()
        return dt.isoformat(timespec="milliseconds")
    except (ValueError, TypeError):
        raise ValueError("Timestamp must be ISO 8601 with timezone, not over 5 minutes in the future")


def normalize(row):
    if not isinstance(row, dict):
        raise ValueError("Each event must be an object")
    action = row.get("kind", row.get("action", ""))
    if not isinstance(action, str) or not isinstance(row.get("source"), str) or not isinstance(row.get("message"), str):
        raise ValueError("source, action/kind, and message must be strings")
    action = {"auth_failure": "login_failed", "auth_success": "login_success"}.get(action, action)
    source = str(row.get("source", ""))[:80]
    message = str(row.get("message", ""))[:4000]
    if not source or not action or not message:
        raise ValueError("source, action (or kind), and message are required")
    severity = row.get("severity", "low")
    if severity not in ["info", "low", "medium", "high", "critical"]:
        raise ValueError("Invalid severity")
    details = row.get("details", {})
    if not isinstance(details, dict):
        raise ValueError("details must be an object")
    port = row.get("port")
    if port not in (None, ""):
        try:
            port = int(port)
            if not 0 <= port <= 65535:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError("port must be an integer between 0 and 65535")
    # Provenance and live dataset are selected by the authenticated endpoint, never by a log.
    return dict(ts=timestamp(row.get("timestamp", row.get("ts", now()))), source=source,
                action=str(action)[:80], message=message, severity=severity,
                host=str(row.get("host", "unknown"))[:120],
                ip=str(row.get("ip", "unknown"))[:80], user=str(row.get("username", row.get("user", "unknown")))[:120],
                port=port, origin="collector",
                dataset="live", external_id=str(row["external_id"])[:180] if row.get("external_id") else None,
                details=details)


def create_app(data_dir=None):
    data_dir = Path(data_dir or os.environ.get("NETWORK_KNIGHT_DATA", ROOT / "backend" / "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    keyfile = data_dir / "collector-key.txt"
    if not keyfile.exists():
        keyfile.write_text(secrets.token_hex(32), encoding="utf-8")
    key = keyfile.read_text().strip()
    db = sqlite3.connect(data_dir / "network-knight.sqlite", check_same_thread=False)
    db.row_factory = sqlite3.Row
    db.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, ts TEXT, source TEXT, host TEXT,
      ip TEXT, user TEXT, action TEXT, severity TEXT, message TEXT, port TEXT, origin TEXT,
      dataset TEXT NOT NULL, external_id TEXT, details TEXT);
    CREATE UNIQUE INDEX IF NOT EXISTS dedup ON events(dataset,source,host,external_id) WHERE external_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS detection_window ON events(dataset,action,source,host,ip,user,ts);
    CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, ruleId TEXT, title TEXT, severity TEXT,
      status TEXT, createdAt TEXT, updatedAt TEXT, group_key TEXT, dataset TEXT, eventIds TEXT);
    CREATE TABLE IF NOT EXISTS collectors(id TEXT PRIMARY KEY,last_seen TEXT,status TEXT,detail TEXT);
    CREATE TABLE IF NOT EXISTS service_activity(id INTEGER PRIMARY KEY, service TEXT, state TEXT, message TEXT, createdAt TEXT);
    """)
    if 'checks' not in {r[1] for r in db.execute('PRAGMA table_info(collectors)')}:
        db.execute("ALTER TABLE collectors ADD COLUMN checks TEXT NOT NULL DEFAULT '{}'")
        db.commit()
    lock = threading.RLock()
    @asynccontextmanager
    async def lifespan(api):
        runtime = api.state.runtime
        if runtime:
            runtime.start()
        try:
            yield
        finally:
            if runtime:
                await run_in_threadpool(runtime.stop)
                print('[STOPPED] Network Knight managed collectors have stopped.', flush=True)
                with lock, db:
                    db.execute('INSERT INTO service_activity(service,state,message,createdAt) VALUES(?,?,?,?)',
                               ('backend', 'stopped', 'Network Knight stopped; its managed collectors were stopped.', now()))
    api = FastAPI(title="Network Knight", version="2.1.0", lifespan=lifespan)
    api.state.db = db
    api.state.key = key
    api.state.runtime = None
    api.state.data_dir = data_dir
    api.state.started_at = time.time()
    api.state.service_states = {}
    preferences = Preferences(data_dir)

    def services_snapshot(collectors):
        services = [dict(id='backend', name='FastAPI server', enabled=True, state='running', pid=os.getpid(),
                         detail='Local API and dashboard are responding.', last_seen=now())]
        if api.state.runtime:
            services.extend(api.state.runtime.snapshot(collectors))
        else:
            for service, enabled in preferences.read().items():
                prefix = 'protection:' if service == 'protection' else 'windows:'
                matches = [c for c in collectors if c['id'].startswith(prefix)]
                latest = max(matches, key=lambda c: c['last_seen']) if matches else None
                services.append(collector_status(service, enabled, latest))
        with db:
            for service in services:
                if api.state.service_states.get(service['id']) != service['state']:
                    api.state.service_states[service['id']] = service['state']
                    db.execute('INSERT INTO service_activity(service,state,message,createdAt) VALUES(?,?,?,?)',
                               (service['id'], service['state'], service['name'] + ': ' + service['detail'], now()))
        return services

    @api.middleware("http")
    async def local_only(req, call_next):
        host = req.headers.get("host", "")
        if host.split(":")[0] not in ("127.0.0.1", "localhost", "testserver"):
            return JSONResponse({"detail": "Localhost access only"}, 403)
        if req.headers.get("origin") and req.headers["origin"] != f"http://{host}":
            return JSONResponse({"detail": "Cross-origin request denied"}, 403)
        response = await call_next(req)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'"
        return response

    async def bounded_body(req):
        chunks = bytearray()
        async for chunk in req.stream():
            chunks.extend(chunk)
            if len(chunks) > MAX_BYTES:
                raise HTTPException(413, "Maximum request size is 1 MiB")
        return bytes(chunks)

    async def json_body(req):
        try:
            body = json.loads(await bounded_body(req))
            if not isinstance(body, dict):
                raise ValueError()
            return body
        except (ValueError, UnicodeError):
            raise HTTPException(400, "Expected a JSON object")

    def dashboard(req):
        if req.headers.get("x-network-knight") != "dashboard":
            raise HTTPException(403, "Dashboard header required")

    def authenticate(req):
        if not secrets.compare_digest(req.headers.get("authorization", ""), "Bearer " + key):
            raise HTTPException(401, "Collector key required")

    def event(row):
        e = dict(row)
        e["id"] = str(e["id"])
        e["details"] = json.loads(e["details"])
        return e

    def alert(row):
        a = dict(row)
        a["id"] = str(a["id"])
        a["eventIds"] = json.loads(a["eventIds"])
        rule = next(r for r in RULES if r["id"] == a["ruleId"])
        a.update(reason=rule["logic"] + ". A match is evidence for review, not proof of compromise.",
                 ip="See linked evidence", user="See linked evidence", evidence=[],
                 steps=["Check the source, host, account and timestamps in the evidence.",
                        "Confirm whether the activity was expected or authorized.",
                        "Record findings and acknowledge or resolve this alert."], key=a.pop("group_key"))
        return a

    def ingest(rows):
        accepted = 0
        with lock, db:
            for e in sorted(rows, key=lambda r: r["ts"]):
                values = {**e, "details": json.dumps(e["details"])}
                cols = list(values)
                cur = db.execute(f"INSERT OR IGNORE INTO events({','.join(cols)}) VALUES({','.join('?' for _ in cols)})", list(values.values()))
                if cur.rowcount:
                    e["id"] = cur.lastrowid
                    detect(db, e)
                    accepted += 1
        return dict(accepted=accepted, duplicates=len(rows) - accepted)

    @api.get("/api/health")
    def health():
        return dict(name="Network Knight", backend="FastAPI", storage="SQLite", version='2.1.0', pid=os.getpid(),
                    startedAt=datetime.fromtimestamp(api.state.started_at, timezone.utc).isoformat(),
                    uptime_seconds=int(time.time()-api.state.started_at), instance_id=instance_id(data_dir),
                    managed=api.state.runtime is not None)

    @api.get("/api/state")
    def state(dataset: str = "live"):
        if dataset != "live":
            raise HTTPException(400, "Only real local collector data is available")
        with lock:
            events = [event(r) for r in db.execute("SELECT * FROM events WHERE dataset=? ORDER BY id DESC LIMIT 10000", (dataset,))]
            alerts = [alert(r) for r in db.execute("SELECT * FROM alerts WHERE dataset=? ORDER BY id DESC LIMIT 1000", (dataset,))]
            # Always include evidence for visible alerts, even when older than the event stream limit.
            evidence_ids = {i for a in alerts for i in a["eventIds"]}
            present = {e["id"] for e in events}
            for i in evidence_ids - present:
                r = db.execute("SELECT * FROM events WHERE id=? AND dataset=?", (i, dataset)).fetchone()
                if r:
                    events.append(event(r))
            total = db.execute("SELECT count(*) FROM events WHERE dataset=?", (dataset,)).fetchone()[0]
            collectors = [{**dict(r), 'checks': json.loads(r['checks'])} for r in db.execute('SELECT * FROM collectors')]
            services = services_snapshot(collectors)
            return dict(version=1, seq=0, events=events, alerts=alerts, dataset=dataset, total=total,
                        truncated=total > len(events), rules=RULES,
                        collectors=collectors, services=services, monitoring_status=overall_status(services),
                        service_activity=[dict(r) for r in db.execute('SELECT * FROM service_activity ORDER BY id DESC LIMIT 30')],
                        managed=api.state.runtime is not None, uptime_seconds=int(time.time()-api.state.started_at), now=now())

    @api.post('/api/services/{service}')
    async def configure_service(service: str, req: Request):
        dashboard(req)
        if service not in ('protection', 'windows', 'all'):
            raise HTTPException(404, 'Unknown component')
        enabled = (await json_body(req)).get('enabled')
        if not isinstance(enabled, bool):
            raise HTTPException(400, 'enabled must be true or false')
        if api.state.runtime is None:
            raise HTTPException(409, 'Start with Start-Network-Knight.cmd to manage components')
        await run_in_threadpool(api.state.runtime.set_enabled, service, enabled)
        return dict(updated=True, enabled=enabled)

    @api.post('/api/services/{service}/restart')
    async def restart_service(service: str, req: Request):
        dashboard(req)
        if service not in ('protection', 'windows'):
            raise HTTPException(404, 'Unknown component')
        if api.state.runtime is None:
            raise HTTPException(409, 'Start with Start-Network-Knight.cmd to manage components')
        try:
            await run_in_threadpool(api.state.runtime.restart, service)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return dict(restarted=True)

    @api.post("/api/ingest")
    async def collect(req: Request):
        authenticate(req)
        body = await json_body(req)
        try:
            rows = body.get("events")
            if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
                raise ValueError("Send 1–500 events")
            normalized = [normalize(e) for e in rows]
            return ingest(normalized)
        except ValueError as exc:
            raise HTTPException(400, str(exc))

    @api.patch("/api/alerts/{alert_id}")
    async def update(alert_id: int, req: Request):
        dashboard(req)
        status = (await json_body(req)).get("status")
        if status not in ("open", "acknowledged", "resolved"):
            raise HTTPException(400, "Invalid alert status")
        with lock, db:
            cur = db.execute("UPDATE alerts SET status=?,updatedAt=? WHERE id=?", (status, now(), alert_id))
            if not cur.rowcount:
                raise HTTPException(404, "Alert not found")
        return dict(updated=True)

    @api.post("/api/heartbeat")
    async def heartbeat(req: Request):
        authenticate(req)
        body = await json_body(req)
        if not isinstance(body.get("id"), str) or not body["id"].strip():
            raise HTTPException(400, "Collector id required")
        checks = body.get("checks", {})
        allowed = {"defender", "firewall:Public", "firewall:Private", "firewall:Domain"}
        if not isinstance(checks, dict) or any(k not in allowed or not isinstance(v, bool) for k, v in checks.items()):
            raise HTTPException(400, "Protection checks must be named boolean states")
        with lock, db:
            db.execute("INSERT INTO collectors(id,last_seen,status,detail,checks) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,status=excluded.status,detail=excluded.detail,checks=excluded.checks", (body["id"][:160], now(), str(body.get("status", "ok"))[:80], str(body.get("detail", ""))[:2000], json.dumps(checks)))
        return dict(ok=True)

    @api.get("/{file_path:path}")
    def frontend(file_path: str):
        if file_path.startswith(("api/", "backend/", ".")):
            raise HTTPException(404)
        dist = (ROOT / "dist").resolve()
        target = (dist / file_path).resolve()
        if not target.is_relative_to(dist):
            raise HTTPException(404)
        if target.is_file():
            return FileResponse(target)
        if "." not in file_path and (dist / "index.html").exists():
            return FileResponse(dist / "index.html")
        raise HTTPException(404, "Frontend missing; build React with npm install and npm run build")

    return api


app = create_app()
