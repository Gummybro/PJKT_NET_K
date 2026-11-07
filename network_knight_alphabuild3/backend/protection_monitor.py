"""Read-only V1 Windows Defender/firewall collector. No file or folder monitoring."""
import argparse
import getpass
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import urllib.request
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent

def make_event(action, message, severity='info', **details):
    return dict(timestamp=datetime.now(timezone.utc).isoformat(), source='protection-monitor',
                host=platform.node() or 'local-laptop', user=getpass.getuser(), ip='127.0.0.1',
                action=action, severity=severity, message=message,
                external_id='protection:' + uuid.uuid4().hex, details=details)

def protection_events(previous, current):
    events = []
    for name, enabled in current.items():
        if not isinstance(enabled, bool) or previous.get(name) == enabled:
            continue
        if name == 'defender':
            action = ('protection_restored' if name in previous else 'protection_status') if enabled else 'defender_disabled'
            message = 'Microsoft Defender antivirus and real-time protection enabled' if enabled else 'Microsoft Defender antivirus or real-time protection is OFF'
        else:
            action = ('protection_restored' if name in previous else 'protection_status') if enabled else 'firewall_disabled'
            message = f'Windows Firewall {name.removeprefix("firewall:")} profile is ' + ('ON' if enabled else 'OFF')
        events.append(make_event(action, message, 'info' if enabled else 'high',
                                 protection=name, enabled=enabled,
                                 observation='Current configuration read by PowerShell; not a claim about who changed it'))
    return events


def read_protection():
    if os.name != 'nt':
        return {}, ['Windows protection checks unavailable on this operating system']
    script = r'''
    $ErrorActionPreference='Stop';$values=@{};$problems=@()
    try {
      $d=Get-MpComputerStatus
      if($null -eq $d.RealTimeProtectionEnabled -or $null -eq $d.AntivirusEnabled){throw 'Missing Defender status fields'}
      $values.defender=([bool]$d.RealTimeProtectionEnabled -and [bool]$d.AntivirusEnabled)
    } catch {$problems+=('Defender: '+$_.Exception.Message)}
    try {
      $profiles=@(Get-NetFirewallProfile -PolicyStore ActiveStore)
      if(!$profiles.Count){throw 'No firewall profiles returned'}
      foreach($p in $profiles){
        if([int]$p.Enabled -notin @(0,1)){throw 'Unknown firewall enabled state'}
        $values['firewall:'+$p.Name]=([int]$p.Enabled -eq 1)
      }
    } catch {$problems+=('Firewall: '+$_.Exception.Message)}
    @{values=$values;problems=@($problems)}|ConvertTo-Json -Compress -Depth 4
    '''
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, text=True, timeout=20,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise OSError(result.stderr.strip()[:400] or 'PowerShell check failed')
        data = json.loads(result.stdout.lstrip('\ufeff'))
        return data['values'], data['problems']
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {}, ['Protection status unavailable: ' + str(exc)]


def post(url, key, path, body):
    req = urllib.request.Request(url + path, data=json.dumps(body).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)


class Monitor:
    def __init__(self, state_path):
        self.state_path = state_path
        self.state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else dict(protection={}, pending=[])
        self.checks = {}

    def save(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.state), encoding='utf-8')
        temporary.replace(self.state_path)

    def poll(self, protection_reader=read_protection):
        values, problems = protection_reader()
        self.checks = values
        if len(self.state['pending']) >= 20000:
            return problems + ['Outbox full; reconnect backend before further monitoring']
        self.state['pending'].extend(protection_events(self.state['protection'], values))
        self.state['protection'].update(values)
        self.save()
        return problems

    def flush(self, url, key):
        sent = 0
        while self.state['pending']:
            batch = self.state['pending'][:200]
            result = post(url, key, '/api/ingest', {'events': batch})
            sent += result['accepted']
            del self.state['pending'][:len(batch)]
            self.save()
        return sent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8787')
    parser.add_argument('--interval', type=float, default=5)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    from urllib.parse import urlparse
    target = urlparse(args.url)
    if target.scheme != 'http' or target.hostname not in ('127.0.0.1', 'localhost') or target.path not in ('', '/') or target.username:
        parser.error('Only a local http://127.0.0.1:port backend is supported')
    data = Path(os.environ.get('NETWORK_KNIGHT_DATA', ROOT / 'backend/data'))
    keyfile = data / 'collector-key.txt'
    if not keyfile.exists():
        parser.error('Start Network Knight first so its collector key is created')
    key = keyfile.read_text(encoding='utf-8').strip()
    # Avoid concurrent monitors competing for one retry outbox.
    lockfile = (data / 'protection-monitor.lock').open('a+b')
    if os.name == 'nt':
        import msvcrt
        lockfile.seek(0);lockfile.write(b'0');lockfile.flush();lockfile.seek(0)
        try:msvcrt.locking(lockfile.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:parser.error('Protection monitor is already running for this installation')
    monitor = Monitor(data / 'protection-monitor.json')
    print('Network Knight V1 protection monitor. Read-only Defender/firewall checks. Ctrl+C stops it.', flush=True)
    try:
        while True:
            started = time.monotonic()
            problems = monitor.poll()
            try:
                count = monitor.flush(args.url.rstrip('/'), key)
                detail = ' | '.join(problems) if problems else 'Microsoft Defender and Windows Firewall status checked; uploaded %s events.' % count
                post(args.url.rstrip('/'), key, '/api/heartbeat', dict(id='protection:' + platform.node(),
                     status='degraded' if problems else 'ok', detail=detail, checks=monitor.checks))
                print(detail, flush=True)
            except (OSError, ValueError) as exc:
                print(f'Backend unavailable; {len(monitor.state["pending"])} events queued: {exc}', flush=True)
            if args.once:
                break
            time.sleep(max(.1, max(1, args.interval) - (time.monotonic() - started)))
    except KeyboardInterrupt:
        print('Protection monitor stopped; pending events preserved.')
    finally:
        lockfile.close()


if __name__ == '__main__':
    main()
