# Real local monitoring verification — October 29, 2026

- Python 3.10.20, Node 24.18.0, Windows host.
- 18 isolated backend integration tests pass: detection/evidence, boundaries/grouping, actual Windows timestamp format, request/auth protections, removed simulation/lab/upload endpoints, schema migration, persistence, protection transitions/no-repeat, heartbeat states and durable retry/deduplication.
- Real socket HTTP smoke test passes with actual local Defender/firewall readings and an isolated temporary database. No synthetic records are written by this smoke test.
- React production build passes; sample buttons/dataset selector and assets are removed. Real-only source/guide screens are included.
- Actual protection monitor successfully read Defender and all firewall profiles ON. No security settings were disabled. OFF transitions are verified only in isolated unit fixtures; the application will record them when actually observed.
- Real Windows collector successfully ingested 151 records from System, Application and Defender Operational in the initial verification. Four protection-status observations were also stored. One real service-installation record triggered WIN-003. Subsequent live counts can grow.
- Security channel access was denied under the current Windows account/token. It is correctly shown as degraded; starting the launcher as Administrator is generally needed. No Security-channel coverage is claimed until a fresh healthy channel reading confirms it.
- All 49 earlier sample events and their sample alerts were removed from the working database; zero non-live rows remain. Shared ZIP contains no runtime database or secret keys at all.
- All configured Windows channel records are collected, not only known alert IDs. Windows timestamps with seven fractional digits now normalize correctly on Python 3.10; the regression test passes.
- PowerShell parser test passes for eight mappings and group SID evidence (isolated XML).
- No file/folder monitoring, sample data generators or rejecting lab endpoints remain. Unconnected web/port-probing rules are removed from the active catalog (14 rules remain).

## Practical limits

Collectors poll about every five seconds, dashboard every two seconds, plus query/processing/backlog delay. Auditing, permissions, retention and laptop sleep affect collection. Only the configured channels and Microsoft Defender/Windows Firewall status are currently connected. Third-party antivirus and arbitrary network/application logs are not automatically collected.

## Reproduce

Setup-Windows.cmd; Test-Network-Knight.cmd; Start-Network-Knight.cmd (as Administrator for Security channel access). Check Overview protection cards, Data Sources health and Event Logs for actual laptop records.

- Final browser verification: Overview showed LIVE LOCAL DATA, four actual protection cards ON, 155 collected real records and the real service alert. Event Logs displayed actual Defender/System/Application messages with collector provenance; no sample controls or dataset selector were present.
