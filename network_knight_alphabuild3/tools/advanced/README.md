# Advanced launchers

General users should use only [Start-Network-Knight.cmd](../../Start-Network-Knight.cmd). It handles setup and starts the server and both collectors together.

| Command | Purpose |
| --- | --- |
| Setup-Windows.cmd | Install/check dependencies without starting monitoring |
| Start-Protection-Monitor.cmd | Manually start protection collection when using an API-only setup |
| Start-Windows-Collector.cmd | Manually start Windows collection when using an API-only setup |
| Enable-All-Monitoring.cmd | Re-enable both Network Knight collectors, now or on next startup |
| Enable-Background-Monitoring.cmd | Optional elevated sign-in task for the server and both supervised collectors |
| Check-Background-Monitoring.cmd | Inspect optional scheduled tasks and latest collector heartbeats |
| Test-Network-Knight.cmd | Run isolated Python tests and real HTTP/service lifecycle checks |

Do not start manual collectors alongside the unified launcher. To use manual collectors intentionally, start an API-only Uvicorn instance and run the needed manual commands. Per-component controls require the unified supervisor. Background task installation was not exercised in this build; foreground unified startup was verified with actual read-only sources.
