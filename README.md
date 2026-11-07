# PJKT_NET_K · Network Knight

A personal release archive of my Network Knight senior design work. The application collects Windows events and Microsoft Defender and firewall observations, applies detection rules, and presents alerts with their supporting evidence in a local React dashboard. FastAPI serves the dashboard and SQLite stores the records on the monitored computer.

## Releases

| Release | What to explore |
| --- | --- |
| [AlphaBuild 3](network_knight_alphabuild3/README.md) | Current release. Browse events by browser session or across the full history, reset a session with administrator approval, and investigate workstation-lock events. |
| [AlphaBuild 2](network_knight_alphabuild2/README.md) | Unified startup, collector controls, health indicators, and persistent service activity. |
| [AlphaBuild 1](network_knight_alphabuild1/README.md) | Earlier Windows monitoring dashboard and real event detection. |

## Run the current release

1. Download and extract the repository or clone it onto a Windows computer.
2. Install Python 3.11 or newer with the Windows Python launcher.
3. Open **network_knight_alphabuild3** and run **Start-Network-Knight.cmd**. The first run needs internet for Python dependencies. Run as administrator for Windows Security channel access.
4. Keep the terminal open and visit **http://127.0.0.1:8787/**. Check **Data Sources** for collector health before reviewing events.

The React production bundle is included. Each installation monitors its own computer. Runtime logs and collector credentials are created locally.

## Project material

Browse the [documentation index](docs/README.md), [design diagrams](docs/design/README.md), and [dashboard screenshots](assets/screenshots/). Historical reports describe the build available when each report was written.

## Project history

This repository preserves three numbered releases from the [team senior design repository](https://github.com/kosse001/SeniorDesign) at commit d8bd7c2. It complements [my personal project fork](https://github.com/Gummybro/SeniorDesign_alphabuilds). The project incorporates team materials, starter code, and third-party libraries.
