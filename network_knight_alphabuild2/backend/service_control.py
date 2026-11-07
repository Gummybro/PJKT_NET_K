"""Local component preferences, process supervision and truthful health states."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
NAMES = {'protection': 'Protection monitor', 'windows': 'Windows logging'}


def stamp(value=None):
    return datetime.fromtimestamp(value or time.time(), timezone.utc).isoformat(timespec='milliseconds')


def instance_id(data_dir):
    return hashlib.sha256(str(Path(data_dir).resolve()).casefold().encode()).hexdigest()[:20]


class Preferences:
    def __init__(self, data_dir):
        self.path = Path(data_dir) / 'monitoring-settings.json'
        self.lock = threading.RLock()

    def read(self):
        with self.lock:
            values = json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {}
            if not isinstance(values, dict) or any(k not in NAMES or not isinstance(v, bool) for k, v in values.items()):
                raise ValueError('Invalid monitoring-settings.json; expected protection/windows boolean values')
            return {key: values.get(key, True) for key in NAMES}

    def set(self, service, enabled):
        if service not in (*NAMES, 'all') or not isinstance(enabled, bool):
            raise ValueError('Choose protection, windows or all, and a boolean enabled value')
        with self.lock:
            values = self.read()
            for key in NAMES if service == 'all' else [service]:
                values[key] = enabled
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(self.path.name + '.' + uuid.uuid4().hex + '.tmp')
            temporary.write_text(json.dumps(values, indent=2), encoding='utf-8')
            temporary.replace(self.path)
            return values


def collector_status(service, enabled, collector, process=None, now=None):
    """An alive process is not healthy until a fresh heartbeat confirms collection."""
    now = now or time.time()
    result = dict(id=service, name=NAMES[service], enabled=enabled, pid=None,
                  state='starting', detail='Waiting for the first collector heartbeat.', last_seen=None)
    if not enabled:
        return {**result, 'state': 'disabled', 'detail': 'Disabled by you. Enable it to resume collection.'}
    if process:
        result['pid'] = process.get('pid')
        if process.get('error'):
            return {**result, 'state': 'error', 'detail': process['error']}
    seen = None
    if collector:
        try:
            seen = datetime.fromisoformat(collector['last_seen']).timestamp()
        except (ValueError, KeyError, TypeError):
            pass
    started = process.get('started_at', 0) if process else 0
    if seen is not None and seen >= started and 0 <= now - seen <= 30:
        state = {'ok': 'running', 'degraded': 'degraded', 'error': 'error'}.get(collector['status'], 'degraded')
        detail = collector['detail']
        if service == 'windows' and state == 'degraded' and any(s in detail.lower() for s in ('unauthorized', 'access denied', 'access is denied')):
            detail += ' For Security log access, restart Start-Network-Knight.cmd using Run as administrator.'
        return {**result, 'state': state, 'detail': detail, 'last_seen': collector['last_seen']}
    if process and now - started <= 30:
        return result
    return {**result, 'state': 'offline', 'detail': 'No fresh heartbeat for 30 seconds. Monitoring coverage is unavailable.',
            'last_seen': collector.get('last_seen') if collector else None}


def overall_status(services):
    states = {s['state'] for s in services if s['id'] != 'backend'}
    if states & {'error', 'offline'}:
        return 'attention'
    if 'degraded' in states:
        return 'degraded'
    if 'starting' in states:
        return 'starting'
    if 'disabled' in states:
        return 'partial'
    return 'running'


class Supervisor:
    def __init__(self, data_dir, url):
        self.data_dir = Path(data_dir)
        self.preferences = Preferences(data_dir)
        self.url = url
        self.processes = {}
        self.streams = {}
        self.info = {}
        self.lock = threading.RLock()
        self.finished = threading.Event()
        self.thread = None

    def command(self, service):
        if service == 'protection':
            return [sys.executable, '-m', 'backend.protection_monitor', '--url', self.url]
        if os.name != 'nt':
            raise OSError('Windows Event Log collection requires Windows')
        return ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'RemoteSigned',
                '-File', str(ROOT / 'backend/collector/start-collector.ps1'), '-ServerUrl', self.url]

    def _stop(self, service):
        process = self.processes.pop(service, None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        self.info.pop(service, None)
        stream = self.streams.pop(service, None)
        if stream:
            stream.close()

    def reconcile(self):
        with self.lock:
            for service, enabled in self.preferences.read().items():
                if not enabled:
                    self._stop(service)
                    continue
                process = self.processes.get(service)
                if process is not None:
                    code = process.poll()
                    if code is not None:
                        self.info[service]['error'] = f'Process stopped with exit code {code}. Check the terminal, then click Restart.'
                    continue
                if service in self.info:  # Startup failure: leave visible until explicit retry.
                    continue
                try:
                    stream = None
                    if os.environ.get('NETWORK_KNIGHT_BACKGROUND') == '1':
                        logs = self.data_dir / 'background'
                        logs.mkdir(parents=True, exist_ok=True)
                        stream = (logs / (service + '.log')).open('a', encoding='utf-8')
                        self.streams[service] = stream
                    process = subprocess.Popen(self.command(service), cwd=ROOT,
                                               env={**os.environ, 'NETWORK_KNIGHT_DATA': str(self.data_dir.resolve())},
                                               stdout=stream, stderr=subprocess.STDOUT if stream else None,
                                               creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
                    self.processes[service] = process
                    self.info[service] = dict(pid=process.pid, started_at=time.time())
                    print(f'[STARTING] {NAMES[service]} (PID {process.pid}); waiting for heartbeat.', flush=True)
                except OSError as exc:
                    self.info[service] = dict(error=str(exc), started_at=time.time())
                    print(f'[ERROR] {NAMES[service]}: {exc}', flush=True)

    def start(self):
        self.reconcile()
        def watch():
            while not self.finished.wait(1):
                try:
                    self.reconcile()
                except (OSError, ValueError) as exc:
                    print('[ERROR] Monitoring preferences:', exc, flush=True)
        self.thread = threading.Thread(target=watch, daemon=True)
        self.thread.start()

    def set_enabled(self, service, enabled):
        with self.lock:
            self.preferences.set(service, enabled)
            if enabled:
                for key in NAMES if service == 'all' else [service]:
                    if key not in self.processes or self.processes[key].poll() is not None:
                        self._stop(key)
            self.reconcile()

    def restart(self, service):
        with self.lock:
            if service not in NAMES:
                raise ValueError('Unknown component')
            if not self.preferences.read()[service]:
                raise ValueError('Enable this component before restarting it')
            self._stop(service)
            self.reconcile()

    def snapshot(self, collectors):
        with self.lock:
            result = []
            for service, enabled in self.preferences.read().items():
                prefix = 'protection:' if service == 'protection' else 'windows:'
                matches = [c for c in collectors if c['id'].casefold() == (prefix + platform.node()).casefold()]
                latest = max(matches, key=lambda c: c['last_seen']) if matches else None
                result.append(collector_status(service, enabled, latest, self.info.get(service)))
            return result

    def stop(self):
        self.finished.set()
        if self.thread:
            self.thread.join(timeout=3)
        with self.lock:
            for service in NAMES:
                self._stop(service)
