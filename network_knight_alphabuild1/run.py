"""Start FastAPI, the V1 protection monitor, and the local React dashboard."""
import argparse
import os
import platform
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
import uvicorn

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--no-monitor', action='store_true')
    parser.add_argument('--no-windows-collector', action='store_true')
    args = parser.parse_args()
    server = uvicorn.Server(uvicorn.Config('backend.app:app', host='127.0.0.1', port=8787))
    stopped = threading.Event()
    children = []
    def ready():
        reported = set()
        windows = None
        while not stopped.wait(.5):
            if not server.started:
                continue
            if not children and not reported:
                if not args.no_monitor:
                    command = [sys.executable, '-m', 'backend.protection_monitor']
                    children.append(subprocess.Popen(command, cwd=ROOT,
                        creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)))
                if os.name == 'nt' and not args.no_windows_collector:
                    windows = subprocess.Popen(['powershell.exe', '-NoProfile', '-NonInteractive',
                        '-ExecutionPolicy', 'RemoteSigned', '-File', str(ROOT / 'backend/collector/start-collector.ps1')],
                        cwd=ROOT, creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
                    children.append(windows)
                if not args.no_browser:
                    webbrowser.open('http://127.0.0.1:8787/')
                reported.add('started')
            for child in children:
                if child.poll() is not None and child.pid not in reported:
                    reported.add(child.pid)
                    try:
                        from backend.protection_monitor import post
                        data = Path(os.environ.get('NETWORK_KNIGHT_DATA', ROOT / 'backend/data'))
                        key = (data / 'collector-key.txt').read_text().strip()
                        collector_id = ('windows:' if child is windows else 'protection:') + platform.node()
                        post('http://127.0.0.1:8787', key, '/api/heartbeat', dict(id=collector_id,
                             status='error', detail=f'Collector process exited with code {child.returncode}. Check the terminal for permissions, script policy or startup errors.'))
                    except Exception as exc:
                        print('Could not report collector failure:', exc, flush=True)
    thread = threading.Thread(target=ready, daemon=True)
    thread.start()
    try:
        server.run()
    finally:
        stopped.set()
        thread.join(timeout=2)
        for process in children:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)

if __name__ == '__main__':
    main()
