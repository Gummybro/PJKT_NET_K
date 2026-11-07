# Network Knight — Version 1: real local monitoring

FastAPI + React + SQLite. The dashboard displays actual observations from this laptop. There are no simulation buttons, seeded records, sample endpoints, lab login endpoints, sample assets, manual log uploads, or file/folder monitors.

## Exact Windows  setup

1. Extract the entire ZIP to a local folder, such as `C:\Network-Knight`. Do not run inside the ZIP.
2. Install **Python 3.11 or newer** with the Windows `py` launcher from https://www.python.org/downloads/windows/ . Open a new PowerShell window and check `py -3 --version`.
3. Double-click **Setup-Windows.cmd** once. Internet is needed to create `.venv` and install `requirements-lock.txt`.
4. Right-click **Start-Network-Knight.cmd** and choose **Run as administrator** when you want Security log access. Normal double-click can collect channels permitted to your normal account; access errors are shown in Data Sources.
5. The launcher starts FastAPI, the protection monitor and Windows Event Log collector, then opens your default browser at **http://127.0.0.1:8787/**. Keep its terminal open. Ctrl+C stops the server and its child collectors.
6. Open **Data Sources** and confirm both `protection:` and `windows:` heartbeats are fresh. A degraded Windows collector lists the exact channels it cannot read. An accessible API does not imply every channel is readable.

The built React dashboard is included in `dist/`: **Node.js is not required to run the ZIP**. No account, cloud service, subscription, GPU or Lenovo-specific software is needed. The laptop must be awake and the app running.

Manual PowerShell setup from the extracted project folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe run.py
```

`run.py --no-browser` leaves the browser closed until you open the URL. `--no-monitor` skips protection checks; `--no-windows-collector` skips Windows Event Logs. Starting Uvicorn directly starts only the server. The normal launcher starts everything. Stop an old server before starting a second copy on port 8787.

The Windows collector is launched with PowerShell RemoteSigned for that child process only; no saved execution policy or audit policy is changed. Group policy still takes precedence. If a downloaded script is blocked by its Internet mark, review it, then use `Unblock-File -LiteralPath .\backend\collector\start-collector.ps1` and `Unblock-File -LiteralPath .\backend\collector\windows-event.ps1` if permitted by your organization. The dashboard reports collector startup failures; it never fills gaps with generated data.

## Real antivirus / firewall behavior

The automatic protection monitor reads `Get-MpComputerStatus` and `Get-NetFirewallProfile -PolicyStore ActiveStore` about every five seconds. Overview shows actual ON/OFF status with fresh heartbeat data. Missing/failed readings show UNAVAILABLE, not an invented OFF state.

- If **Microsoft Defender antivirus or real-time protection is actually OFF**, the monitor records the observed state, creates high-severity **WIN-010**, and the Defender card becomes OFF. A Defender Operational 5001 event can independently produce the same rule alert.
- If a Windows Firewall Domain, Private or Public profile is actually OFF, the named profile produces **WIN-011** and its status card becomes OFF. Inactive profile settings are still reported as profile settings, not proof that active traffic is unprotected.
- Turning protection ON again records a real recovery event. A previous alert stays open until you review/acknowledge/resolve it.
- An OFF state already present at startup is logged and alerts. Unchanged OFF observations do not flood the dashboard each poll. The durable monitor state remembers previous values across restart.
- Microsoft Defender status is not a universal verdict on other antivirus products. Another installed antivirus can legitimately put Defender into inactive/passive mode. Third-party antivirus health is outside this version's sources.

The app never changes antivirus, firewall, audit settings or accounts. It only reads them. No security settings were disabled during verification. OFF/recovery logic is covered by isolated automated test fixtures; fixtures are never inserted into the running dashboard.

## Real Windows Event Logs

The automatic Windows collector reads **Security, System, Application and Microsoft-Windows-Windows Defender/Operational**. It collects all new records from these configured channels, not only records that trigger alerts. Known security event IDs map to detection actions; other records remain searchable context.

On first run, up to 50 recent actual records per accessible channel are imported so the initial dashboard contains real evidence. Then saved per-channel cursors follow new records. Each channel reads at most 200 records per poll, allowing backlog catch-up. Cursors advance after successful backend acceptance. Stable event IDs prevent duplicates on retry. Previously overwritten records cannot be recovered.

Security normally requires administrator/Event Log Reader permissions and Windows auditing already enabled. The app does not enable auditing. A channel without access is shown degraded while available channels continue. Windows can produce no matching security events if auditing is not configured; no substitute events are generated.

Dashboard fields include original event time, source, host/account/IP when present, severity, normalized action, original message and collector provenance. Windows event ID, record ID, provider and parsed fields are retained in details. Many legitimate Windows events have no IP or username; unknown values remain unknown. Severity uses known rule mappings or the actual Windows level. Rules flag signals for review, not proof of compromise.

## Near-real-time display

Collectors poll approximately every five seconds; React refreshes the API every two seconds. Allow about seven seconds plus Windows processing/query time after a recorded change. Status cards, counters, alert badges, event tables and linked evidence update without manually reloading. New alerts show an in-dashboard toast. Browser background throttling, sleep, slow queries and backlog can delay updates.

Overview and Event Logs show only collected local records. Alerts link to persisted evidence and support Acknowledge, Resolve and Reopen. No simulated dataset selector or generators remain. This version does not capture network packets, monitor arbitrary websites, or collect every third-party application's private logs. Web probing/port-probing rules were removed from the active catalog because those sources are not connected.

## Presentation using real data

1. Start the launcher and show the live Defender/firewall cards.
2. Open Data Sources and show channel health, including any real access limitations.
3. Open Event Logs to show actual System, Application or Defender records. Search by message, action, username or source.
4. When an actual Defender/firewall change is observed, open its new alert and show the linked observation and timestamps. Re-enabling protection should produce a recovery log. The app does not perform the change for you.
5. Review actual Windows alerts as they occur. An imported recent service-installation record, for example, can generate WIN-003; verify whether it was an authorized installation.
6. Acknowledge/resolve an alert, restart the app, and show that evidence and status persist.

## Active rules

| ID | Name | Severity | Logic |
| --- | --- | --- | --- |
| AUTH-001 | Failed login burst | high | 5 failed logins in 60 seconds, same source, host, IP and user |
| WIN-001 | Windows audit log cleared | critical | Security event 1102 |
| WIN-002 | Windows account created | medium | Security event 4720; verify authorization |
| WIN-003 | Windows service installed | medium | System 7045 / Security 4697; verify authorization |
| WIN-004 | Defender threat detected | high | Defender event 1116 |
| AUTH-002 | Successful login after failures | high | A successful login following 5 failures in 5 minutes for the same source, host, IP and user |
| AUTH-003 | Possible password spraying | high | 10 failed logins across at least 5 known usernames in 5 minutes from the same known IP, source and host |
| WIN-005 | Windows account locked out | medium | Security event 4740; investigate repeated authentication failures |
| WIN-006 | Windows account deleted | medium | Security event 4726; verify authorization |
| WIN-007 | Administrative group member added | high | Group member addition to local Administrators, Domain Admins or Enterprise Admins, identified by group SID |
| WIN-008 | Windows audit policy changed | high | Security event 4719; review the recorded audit policy change |
| WIN-009 | Windows scheduled task created | medium | Security event 4698; review the recorded task and author |
| WIN-010 | Defender real-time protection disabled | high | Defender Operational event 5001, or antivirus/real-time protection observed OFF |
| WIN-011 | Windows Firewall profile disabled | high | A Windows Firewall profile is observed disabled, initially or after a change |

Batch records sort by event time. Authentication rules correlate source, host, IP and account as appropriate. Very late events across separate uploads are not fully re-correlated. Burst evidence merges for 60 seconds; an existing resolved alert stays resolved during the merge window. Independent protection and Windows collectors may both report one Defender change, producing separate evidence-linked alerts.

## Verification commands

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -v
.\.venv\Scripts\python.exe tools/verify_http.py
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File backend/tests/windows_rules.test.ps1
```

Or run **Test-Network-Knight.cmd** for the Python integration suite and real HTTP smoke test. Unit/integration tests use temporary databases to validate threshold, OFF/recovery and failure cases; they never touch the active monitor database. The HTTP smoke test uses actual read-only device protection readings, starts/stops an isolated server and verifies removed simulation routes, static React serving and restart persistence. The PowerShell parser test uses isolated XML fixtures only. See VERIFICATION.md for current results.

## Build React

Install Node.js 22.13+ (tested with 24.18.0), then:

```powershell
npm ci
npm run build
```

Refresh the FastAPI-served browser page after rebuilding. `package-lock.json` pins the frontend build dependencies. Use one Uvicorn worker for the embedded SQLite connection.

## Storage, local API and operational limits

- `run.py`: API startup, both collector processes, browser opening and collector shutdown.
- `backend/app.py`: FastAPI, bounded authenticated ingestion, SQLite and React serving.
- `backend/protection_monitor.py`: actual Defender/firewall readings, durable retry outbox, heartbeat.
- `backend/collector/`: actual Windows event parser/collector and saved cursors.
- `backend/detection.py`: 14 active rules connected to current Windows/protection sources.
- `src/` and `dist/`: editable React source and included production build.

Routes: GET `/api/health`, GET `/api/state`, POST `/api/ingest`, POST `/api/heartbeat`, PATCH `/api/alerts/{id}`. Collector writes require the generated Bearer key in `backend/data/collector-key.txt`. Dashboard status changes require `X-Network-Knight: dashboard`. The key is never sent to React. Input batches are bounded to 1 MiB/500 records, validated atomically, then stored and detected in one transaction. Only the live dataset is exposed.

`backend/data/` contains SQLite events/alerts, collector key/cursors and protection monitor state. Back it up with the app stopped. Do not share it: real local logs can contain account/host information. The project ZIP excludes runtime records, secrets, dependencies and temporary test databases. On this working installation, earlier fabricated records were removed; real collector observations were preserved. A fresh extracted ZIP starts a new database and populates it only from actual local collectors.

The server binds to 127.0.0.1, rejects foreign Host/Origin requests and is intended for one trusted local user. No production login/TLS, cloud AI, automatic blocking or retention policy is included. The UI loads up to 10,000 newest events plus linked evidence and 1,000 alerts. Charts/filters/exports cover loaded records. Disk usage grows until managed by the operator.

The inherited advanced background-task tools start the backend and Windows Event collector separately; the ordinary launcher is the supported Version 1 path for starting both collectors. Do not run manual and scheduled copies together.

## Source provenance

Both user-provided Network Knight ZIPs in Downloads were inspected. The FastAPI/React starter was selected. The standalone Sentinel ZIP and `/mnt/data` paths were unavailable on this Windows host. The final version removes seed fixtures, simulation/lab/upload routes, generated-source controls and file monitoring, adds direct protection polling, automatically starts Windows collection and fixes Windows seven-digit fractional timestamps for Python 3.10 compatibility.

Read-only API references: https://learn.microsoft.com/en-us/powershell/module/defender/get-mpcomputerstatus , https://learn.microsoft.com/en-us/powershell/module/netsecurity/get-netfirewallprofile , https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent .
