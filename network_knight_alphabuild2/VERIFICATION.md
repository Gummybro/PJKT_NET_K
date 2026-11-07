# Unified setup, startup and system feedback verification — October 29, 2026

## Verified

- **29 backend/setup/control tests pass.** Coverage includes existing detections and real Windows timestamp parsing, setup reuse and package-install failure, persisted component choices, authentication, process failure/restart, stale heartbeats, heartbeat after process restart, case-insensitive Windows hostname matching, status history, and refusal to claim control over unmanaged collectors.
- **Clean first-time dependency setup passes.** In an isolated folder without a virtual environment, bootstrap.py created one, installed all 18 locked packages, verified them and reported setup complete. An existing verified installation skips package downloads/reinstallation.
- **The actual Start-Network-Knight.cmd path passes.** It verified the existing environment and started FastAPI plus the protection and Windows collectors together, with progress, permission warning and ready messages.
- **Real service lifecycle HTTP smoke test passes** (tools/verify_services.py). It starts an isolated real managed instance, observes protection running and Windows logging degraded due to actual Security permission denial, disables only Windows logging, restarts protection, restarts the whole app to verify the disable choice persisted, enables everything, and verifies recorded graceful shutdowns. It changes only Network Knight component state, never Windows antivirus/firewall settings.
- **Real HTTP persistence smoke test passes** (tools/verify_http.py). It checks actual protection readings, disabled sample/lab/upload routes, static React routes and SQLite restart persistence.
- **React production build passes**, 1,837 modules, with the new System status panel, per-component controls and service activity.
- **Browser verification passes.** Overview shows actual FastAPI PID/Running, protection PID/Running, and Windows PID/Limited access with the actual denied Security-channel message. Clicking Windows Disable changes it to Disabled by you while protection stays Running; Enable starts a new PID and shows Starting until the new heartbeat. An already-open tab whose test server was stopped shows Server offline/unreachable, collector health Unknown, disabled controls and protection readings UNAVAILABLE. Actual local event records remain visible as retained evidence.
- **PowerShell syntax checks pass** for the revised collector and optional background installer. The existing Windows parser mappings remain unchanged.
- Runtime data, local keys, dependencies and temporary test folders are excluded from the shared ZIP. No simulated security events or sample generators were added. Service activity is a separate history of real application state changes.

## Practical limits

- Python remains a one-time prerequisite; the project installs its own dependencies automatically after Python is available. Node is not needed to run the included dashboard.
- Administrator rights/auditing are still needed for Windows Security logs. This test account has read access to System/Application/Defender but the Security channel is denied. Limited coverage is reported rather than treated as healthy.
- Collectors poll roughly every five seconds, React every two. Missing heartbeats become offline after 30 seconds. Sleep, query delays, backlog and browser background throttling affect timing.
- Foreground monitoring requires its terminal to remain open. Optional scheduled background installation is separate and opt-in. The consolidated scheduled-task script is syntax-checked but actual task registration/sign-in execution was not performed.
- Feedback is in the terminal and dashboard (persistent status, toasts, service activity). No separate Windows notification service was installed.
- Publication check on November 2, 2026: all 29 tests passed again from network_knight_alphabuild2. Prebuilt React assets were copied unchanged from the verified uploaded ZIP; this version is being published in its own folder, preserving alphabuild1.

## Reproduce

Start-Network-Knight.cmd is the general-user entry point. Test commands are in tools/advanced or README.md. Use Data Sources to inspect status and service activity; use the root Disable commands or dashboard controls to pause individual Network Knight collectors.
