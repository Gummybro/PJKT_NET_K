"""Verify unified real collectors, persisted choices and graceful lifecycle over actual HTTP."""
import json,os,signal,socket,sqlite3,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def main():
 with tempfile.TemporaryDirectory(prefix='tmp-unified-',dir=ROOT/'backend/tests') as directory:
  assert Path(directory).resolve().is_relative_to((ROOT/'backend/tests').resolve())
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  url=f'http://127.0.0.1:{port}'
  env={**os.environ,'NETWORK_KNIGHT_DATA':directory}
  def request(path,body=None):
   data=json.dumps(body).encode() if body is not None else None
   req=urllib.request.Request(url+path,data=data,headers={'Content-Type':'application/json','X-Network-Knight':'dashboard'})
   with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
  def wait_for(check,timeout=40):
   end=time.monotonic()+timeout
   while time.monotonic()<end:
    try:
     value=request('/api/state')
     if check(value):return value
    except OSError:pass
    time.sleep(.5)
   raise AssertionError('Timed out waiting for actual service state')
  def start():
   log=open(Path(directory)/'launcher.log','a',encoding='utf-8')
   process=subprocess.Popen([sys.executable,'run.py','--no-browser','--port',str(port)],cwd=ROOT,env=env,
        stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NEW_PROCESS_GROUP',0))
   return process,log
  def stop(process,log):
   if process.poll() is None:
    process.send_signal(signal.CTRL_BREAK_EVENT if os.name=='nt' else signal.SIGINT)
    try:process.wait(timeout=20)
    except subprocess.TimeoutExpired:
     process.terminate();process.wait(timeout=10);raise AssertionError('Launcher did not stop gracefully')
   log.close();time.sleep(1)
  process,log=start()
  try:
   state=wait_for(lambda d: len(d['services'])==3 and all(s['state'] not in ('starting','offline') for s in d['services']))
   assert state['managed']
   assert all(e['origin']=='collector' for e in state['events'])
   print('Actual initial services:',[(s['id'],s['state']) for s in state['services']])
   request('/api/services/windows',{'enabled':False})
   state=wait_for(lambda d:next(s for s in d['services'] if s['id']=='windows')['state']=='disabled')
   assert next(s for s in state['services'] if s['id']=='protection')['state'] in ('running','degraded')
   settings=json.loads((Path(directory)/'monitoring-settings.json').read_text())
   assert settings=={'protection':True,'windows':False}
   before=next(s for s in state['services'] if s['id']=='protection')['pid']
   request('/api/services/protection/restart',{})
   state=wait_for(lambda d:next(s for s in d['services'] if s['id']=='protection')['state'] in ('running','degraded'))
   assert next(s for s in state['services'] if s['id']=='protection')['pid']!=before
  finally:stop(process,log)
  # A normal app restart must respect the user's earlier per-component choice.
  process,log=start()
  try:
   state=wait_for(lambda d:next(s for s in d['services'] if s['id']=='protection')['state'] in ('running','degraded'))
   assert next(s for s in state['services'] if s['id']=='windows')['state']=='disabled'
   request('/api/services/all',{'enabled':True})
   state=wait_for(lambda d:next(s for s in d['services'] if s['id']=='windows')['state'] in ('running','degraded','error'))
   assert next(s for s in state['services'] if s['id']=='windows')['state']!='error',state
  finally:stop(process,log)
  with sqlite3.connect(Path(directory)/'network-knight.sqlite') as db:
   assert db.execute("SELECT count(*) FROM service_activity WHERE service='backend' AND state='stopped'").fetchone()[0]>=2
  db.close()
  print('PASS: actual unified startup, honest limited-access status, individual disable, monitor restart, saved choices across app restart, enable-all and graceful shutdown.')

if __name__=='__main__':main()
