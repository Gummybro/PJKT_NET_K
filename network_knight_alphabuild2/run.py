"""Start one local server supervising both collectors, with visible operational health."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import socket
import sys
import threading
import urllib.request
import webbrowser
import uvicorn
from backend.service_control import Preferences, Supervisor, instance_id

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--no-monitor',action='store_true',help='Disable protection monitoring until enabled again')
    parser.add_argument('--no-windows-collector',action='store_true',help='Disable Windows logging until enabled again')
    parser.add_argument('--port',type=int,default=8787)
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Port must be between 1 and 65535')
    data=Path(os.environ.get('NETWORK_KNIGHT_DATA',ROOT/'backend/data')).resolve()
    os.environ['NETWORK_KNIGHT_DATA']=str(data)
    preferences=Preferences(data)
    preferences.read()
    if args.no_monitor:preferences.set('protection',False)
    if args.no_windows_collector:preferences.set('windows',False)
    url=f'http://127.0.0.1:{args.port}'
    with socket.socket() as probe:
        try:probe.bind(('127.0.0.1',args.port))
        except OSError:
            try:
                with urllib.request.urlopen(url+'/api/health',timeout=3) as response:health=json.load(response)
                if health.get('instance_id')==instance_id(data) and health.get('managed'):
                    print('Network Knight is already running. Opening its dashboard.',flush=True)
                    if not args.no_browser:webbrowser.open(url+'/')
                    return 0
            except (OSError,ValueError):pass
            print(f'Cannot start: port {args.port} is used by another or older instance. Close that server first, or choose --port.',flush=True)
            return 1
    if os.name=='nt' and not ctypes.windll.shell32.IsUserAnAdmin():
        print('[ATTENTION] Standard Windows account: Security channel may be denied. Use Run as administrator for full channel access.',flush=True)
    from backend.app import app
    app.state.runtime=Supervisor(data,url)
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=args.port,access_log=False))
    stopped=threading.Event()
    def ready():
        while not stopped.wait(.2):
            if server.started:
                print(f'[SERVER READY] {url}/ - open the dashboard for individual component status.',flush=True)
                print('Saved disable choices are respected. Enable components from the dashboard or tools/advanced/Enable-All-Monitoring.cmd.',flush=True)
                print('Keep this window open. Ctrl+C stops this app and its collectors. Closing only the browser does not stop monitoring.',flush=True)
                if not args.no_browser:webbrowser.open(url+'/')
                return
    thread=threading.Thread(target=ready,daemon=True);thread.start()
    try:server.run()
    finally:stopped.set();thread.join(timeout=2)
    print('[STOPPED] Network Knight and its managed collectors have stopped.',flush=True)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError) as exc:
        print('START FAILED:',exc,flush=True);sys.exit(1)
