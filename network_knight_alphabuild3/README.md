# Network Knight — local monitoring with one setup-and-start command

FastAPI + React + SQLite, actual local Windows events, actual Defender/firewall observations, and visible component health. No simulated security logs, lab endpoints, sample generators, manual log uploads or file/folder monitoring.

## One command for a general user

1. Extract the entire ZIP into a normal folder. Do not run from inside the ZIP.
2. Install **Python 3.11 or newer with the Windows py launcher** if it is not already installed: https://www.python.org/downloads/windows/ . Python is a one-time prerequisite; the project does not silently install a system-wide Python distribution.
3. Open the extracted `network_knight_alphabuild3` folder and run **Start-Network-Knight.cmd**. For Windows Security log access, right-click it and choose **Run as administrator**.
4. The same command creates the project virtual environment if needed, installs/verifies the required Python packages, starts FastAPI, starts protection monitoring, starts Windows logging, and opens http://127.0.0.1:8787/ . The first package installation needs internet. Later starts reuse verified packages and work without reinstalling them.
5. Keep the terminal window open. The dashboard shows the actual state of each component. Ctrl+C stops the server and its managed collectors; closing only the browser does not stop collection.

You do not need to run a separate setup, logging or protection-monitoring command. The built React dashboard is included; Node.js is only needed to rebuild it. Existing disabled choices are respected rather than silently switched back on.

## Feedback you should see

- Terminal progress: environment check, dependency installation/verification, component starting, server ready and stopped/error messages.
- A **System status** panel on Overview and Data Sources for FastAPI, the protection monitor and Windows logging.
- Each component reports **Starting**, **Running**, **Limited access**, **Offline**, **Failed** or **Disabled by you**, with its PID, latest heartbeat and useful details.
- A live process is not considered healthy until its own fresh heartbeat arrives. A heartbeat from the previous process is not reused after restart. Missing heartbeat for 30 seconds is reported as offline; channel permission failures remain visible as limited coverage.
- In-dashboard notifications for connection/reconnection, collector running/failure/disable transitions, and new security detections. The status banner remains visible after the notification disappears.
- If the server stops or cannot be reached, the dashboard marks it offline/unreachable and marks collector health unknown; it does not keep claiming that monitoring is running. Protection cards then show UNAVAILABLE rather than an old ON/OFF value.
- Data Sources includes **Recent service activity**, a saved history of actual observed application/component changes. These operational messages are separate from security event logs and intrusion alerts.

A running server does not imply every channel is readable. The Security channel normally needs administrator rights. A missing permission is a real visibility gap, not something filled with generated data. These are local application components, not a claim that a Windows Service has been installed.

## Disable only what you choose

The top-level commands are intentionally simple:

| Command | Purpose |
| --- | --- |
| `Start-Network-Knight.cmd` | Set up if necessary and start the whole app |
| `Disable-Protection-Monitor.cmd` | Stop Network Knight's Defender/firewall status collector |
| `Disable-Windows-Logging.cmd` | Stop Network Knight's Windows Event Log collector |
| `Disable-Background-Monitoring.cmd` | Remove optional scheduled background tasks |
| `Check-Network-Knight.cmd` | Print actual server/component health without opening the dashboard |

Disable commands apply immediately when this instance is running, and save the choice for the next start. If it is stopped, the choice is saved for next time. They **do not disable Windows Defender, antivirus, Windows Firewall, or Windows auditing**. They only pause Network Knight's own collection.

The dashboard also has Enable/Disable controls per collector, Restart for a failed/offline collector, and **Enable all monitoring**. To enable collection while the app is closed, use `tools/advanced/Enable-All-Monitoring.cmd`.

Saved preferences: `backend/data/monitoring-settings.json`. No records or existing alert statuses are deleted by these controls.

## Advanced and background operation

Manual component launchers, setup-only, tests and background installation are under [tools/advanced](tools/advanced/README.md). They are for troubleshooting; ordinary users should use only the main Start command.

Optional background installation registers one sign-in task that supervises FastAPI and both collectors. It respects the same disable choices. It is separate from the normal foreground launch and is not installed silently. The task requires administrator setup; the laptop must be awake and the user signed in. Do not run a manual and scheduled copy together. Scheduled-task installation was not executed during this verification.

If a port is occupied by this same managed installation, the launcher opens its existing dashboard without spawning duplicate collectors. If another or older server owns the port, startup stops with an explicit error. Close the old window first. For troubleshooting on another port:

```powershell
.\.venv\Scripts\python.exe run.py --port 8788
```

Windows scripts use RemoteSigned for the child PowerShell process only; no saved policy or audit policy is changed, and organization policies take precedence. If a reviewed downloaded script is blocked by its Internet mark, follow your organization's policy; it may require explicitly unblocking `backend/collector/start-collector.ps1` and `backend/collector/windows-event.ps1`.

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
.\.venv\Scripts\python.exe tools/verify_services.py
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File backend/tests/windows_rules.test.ps1
```

Tests use isolated temporary databases. Detection fixtures never seed the running dashboard. The service lifecycle smoke test launches actual read-only collectors, pauses only Network Knight components, tests saved choices/restart/enable-all and shuts down its isolated instance. It does not change Windows security settings. See [VERIFICATION.md](VERIFICATION.md).

## Rebuild React

Install Node.js 22.13+ (tested with 24.18.0), then:

```powershell
npm ci
npm run build
```

Refresh the FastAPI-served page afterward. The included `package-lock.json` pins the build dependencies. No Node.js is needed after React is built.

## Files and storage

- `bootstrap.py`: first-run environment/package checks and launch orchestration.
- `run.py`: one local server and managed collector lifecycle.
- `backend/service_control.py`: persisted preferences, process supervision, honest health states.
- `backend/app.py`: FastAPI, SQLite, authenticated ingestion, component controls and service activity.
- `backend/protection_monitor.py` and `backend/collector/`: real local collectors.
- `src/` and `dist/`: React source and prebuilt dashboard.
- `tools/advanced/`: optional manual, background and test launchers.

`backend/data/` contains actual logs/alerts, the collector key, acknowledged cursors, preferences and the protection retry outbox. Back it up with the app stopped. Never include it in a source upload or shared ZIP. Component settings and service history survive restarts; security evidence is preserved. This delivery excludes runtime data, dependencies, keys and temporary test databases.

The app is for one trusted local user, binds to 127.0.0.1, and rejects foreign Host/Origin requests. Collector writes require a generated Bearer key; dashboard configuration/status writes require the local dashboard header. No production user login/TLS, automatic threat blocking, email/OS notification service or automatic evidence retention policy is included. Records can grow until managed by the operator. The UI loads up to 10,000 newest events plus linked evidence and 1,000 alerts; charts/filters/export cover loaded records.

Read-only references: https://learn.microsoft.com/en-us/powershell/module/defender/get-mpcomputerstatus , https://learn.microsoft.com/en-us/powershell/module/netsecurity/get-netfirewallprofile , https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent .

## Browser sessions and workstation lock demonstration

Event Logs opens on This session. Each newly opened dashboard tab gets its own
starting event ID. Refreshing the tab preserves that starting point. All logs
searches the full stored history and pages through 50 matches at a time.
Clear session requests Windows administrator approval and advances only that
tab's starting point. New incoming events can appear immediately afterward.

WIN-012 is an informational rule for a real Security 4800 workstation lock.
With Windows logging running, Security readable, and successful Other Logon/Logoff
Events auditing enabled, press Win+L, unlock, and open Alerts to see the linked
record. The application does not change auditing. Investigation tips are fixed
guidance based on the event action.

