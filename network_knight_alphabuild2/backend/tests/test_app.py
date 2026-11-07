"""Isolated test fixtures; never write to the running user's database."""
import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.detection import SINGLE

class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='backend/tests');self.app=create_app(self.tmp.name);self.client=TestClient(self.app)
  self.auth={'Authorization':'Bearer '+self.app.state.key}
 def tearDown(self):
  self.client.close();self.app.state.db.close();self.tmp.cleanup()
 def row(self,**extra):
  return {**dict(source='isolated-test',host='fixture',ip='192.0.2.1',user='fixture-user',action='login_failed',message='ISOLATED TEST FIXTURE'),**extra}
 def ingest(self,rows):return self.client.post('/api/ingest',json={'events':rows},headers=self.auth)
 def state(self):return self.client.get('/api/state').json()
 def test_windows_seven_digit_fractional_timestamp(self):
  response=self.ingest([self.row(timestamp='2026-01-01T12:00:00.1234567Z')])
  self.assertEqual(response.status_code,200,response.text)
  self.assertEqual(self.state()['events'][0]['ts'],'2026-01-01T12:00:00.123+00:00')
 def test_threshold_evidence_and_merge(self):
  self.ingest([self.row() for _ in range(4)]);self.assertEqual(self.state()['alerts'],[])
  self.ingest([self.row()]);self.assertEqual(len(self.state()['alerts'][0]['eventIds']),5)
  self.ingest([self.row()]);self.assertEqual(len(self.state()['alerts']),1);self.assertEqual(len(self.state()['alerts'][0]['eventIds']),6)
 def test_time_and_identity_isolation(self):
  self.ingest([self.row() for _ in range(4)])
  self.ingest([self.row(user='other'),self.row(timestamp=(datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat())])
  self.assertEqual(self.state()['alerts'],[])
 def test_success_after_failures(self):
  self.ingest([*[self.row() for _ in range(5)],self.row(action='login_success')])
  self.assertEqual({a['ruleId'] for a in self.state()['alerts']},{'AUTH-001','AUTH-002'})
 def test_password_spray(self):
  self.ingest([self.row(user=str(i%5)) for i in range(10)])
  self.assertEqual({a['ruleId'] for a in self.state()['alerts']},{'AUTH-003'})
 def test_windows_and_protection_rules(self):
  self.ingest([self.row(action=action) for action in SINGLE])
  self.assertEqual({a['ruleId'] for a in self.state()['alerts']},set(SINGLE.values()))
 def test_admin_group_sid(self):
  self.ingest([self.row(action='group_member_added',details={'fields':{'TargetSid':'S-1-5-32-545'}})])
  self.assertEqual(self.state()['alerts'],[])
  self.ingest([self.row(action='group_member_added',details={'fields':{'TargetSid':'S-1-5-32-544'}})])
  self.assertEqual(self.state()['alerts'][0]['ruleId'],'WIN-007')
 def test_unconnected_sources_have_no_active_rules(self):
  self.ingest([self.row(action='connection_denied',port=p) for p in [22,80,443,445,3389]])
  self.ingest([self.row(action='web_probe') for _ in range(5)])
  self.assertEqual(self.state()['alerts'],[])
 def test_atomic_validation_and_dedup(self):
  row=self.row(external_id='fixture-unique')
  self.assertEqual(self.ingest([row,{}]).status_code,400);self.assertEqual(self.state()['total'],0)
  self.assertEqual(self.ingest([row]).json()['accepted'],1);self.assertEqual(self.ingest([row]).json()['duplicates'],1)
 def test_authentication_and_endpoint_owned_provenance(self):
  self.assertEqual(self.client.post('/api/ingest',json={'events':[self.row()]}).status_code,401)
  self.ingest([self.row(dataset='sample',origin='simulation')]);event=self.state()['events'][0]
  self.assertEqual(event['dataset'],'live');self.assertEqual(event['origin'],'collector')
 def test_simulation_lab_and_upload_are_unavailable(self):
  self.assertEqual(self.client.get('/api/state?dataset=sample').status_code,400)
  for path in ['/api/sample','/api/sample/full','/api/sample/basic','/api/upload','/monitored/login']:
   self.assertIn(self.client.post(path,headers={'X-Network-Knight':'dashboard'},json={}).status_code,(404,405))
  self.assertEqual(self.state()['total'],0)
 def test_request_protections(self):
  self.assertEqual(self.client.post('/api/ingest',content=b'x'*1048577,headers=self.auth).status_code,413)
  self.assertEqual(self.client.get('/api/state',headers={'Origin':'http://evil.invalid'}).status_code,403)
  self.assertEqual(self.client.get('/api/state',headers={'Host':'evil.invalid'}).status_code,403)
 def test_restart_status_persistence(self):
  self.ingest([self.row(action='defender_disabled')]);alert=self.state()['alerts'][0]
  self.client.patch('/api/alerts/'+alert['id'],json={'status':'resolved'},headers={'X-Network-Knight':'dashboard'})
  self.client.close();self.app.state.db.close();self.app=create_app(self.tmp.name);self.client=TestClient(self.app)
  self.assertEqual(self.state()['alerts'][0]['status'],'resolved');self.assertEqual(self.state()['total'],1)
 def test_existing_collector_schema_migrates(self):
  self.client.close();self.app.state.db.close()
  with sqlite3.connect(Path(self.tmp.name)/'network-knight.sqlite') as db:
   db.execute('DROP TABLE collectors');db.execute('CREATE TABLE collectors(id TEXT PRIMARY KEY,last_seen TEXT,status TEXT,detail TEXT)')
   db.execute("INSERT INTO collectors VALUES('legacy','2026-01-01T00:00:00+00:00','ok','fixture')")
  self.app=create_app(self.tmp.name);self.client=TestClient(self.app)
  self.assertEqual(self.state()['collectors'][0]['checks'],{})

if __name__=='__main__':unittest.main()
