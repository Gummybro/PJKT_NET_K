"""Real socket smoke test, isolated DB, real read-only protection observations only."""
import json,os,socket,subprocess,sys,tempfile,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from backend.protection_monitor import Monitor,read_protection

def main():
 with tempfile.TemporaryDirectory() as directory:
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  base=f'http://127.0.0.1:{port}';env={**os.environ,'NETWORK_KNIGHT_DATA':directory}
  def get(path):
   with urllib.request.urlopen(base+path,timeout=5) as r:
    data=r.read();return json.loads(data) if 'json' in r.headers.get('Content-Type','') else data
  def start():
   process=subprocess.Popen([sys.executable,'-m','uvicorn','backend.app:app','--host','127.0.0.1','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   for _ in range(100):
    try:get('/api/health');return process
    except OSError:time.sleep(.1)
   process.terminate();process.wait();raise RuntimeError('Server did not start')
  process=start()
  try:
   assert b'root' in get('/') and b'root' in get('/alerts')
   assert get('/api/state')['total']==0
   for path in ['/api/sample','/api/sample/full','/api/sample/basic','/api/upload','/monitored/login']:
    try:urllib.request.urlopen(urllib.request.Request(base+path,data=b'{}',method='POST'),timeout=5);raise AssertionError('Disabled endpoint accepted request')
    except urllib.error.HTTPError as exc:assert exc.code in (404,405)
   monitor=Monitor(Path(directory)/'protection.json')
   problems=monitor.poll(read_protection)
   key=(Path(directory)/'collector-key.txt').read_text().strip()
   monitor.flush(base,key)
   before=get('/api/state');assert all(e['origin']=='collector' for e in before['events'])
  finally:process.terminate();process.wait(timeout=10);time.sleep(1)
  process=start()
  try:assert get('/api/state')['total']==before['total']
  finally:process.terminate();process.wait(timeout=10);time.sleep(1)
  print('PASS: real HTTP/React routes, disabled sample/lab/upload routes, actual protection readings and SQLite restart persistence')
  if problems:print('Protection query limitations:',problems)
if __name__=='__main__':main()
